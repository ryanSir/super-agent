"""Orchestrator Agent 定义

系统的"Python 大脑"，基于 PydanticAI 实现 Orchestrator-Workers 编排模式。
负责意图理解、DAG 规划、任务路由分发、结果整合。
"""

# 标准库
import asyncio
import json
import shlex
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

# 第三方库
import pydantic_core
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, ToolCallPart
from pydantic_ai.models.instrumented import InstrumentationSettings


# ============================================================
# Monkey-patch: 修复网关流式转发导致的 tool call JSON 截断
#
# rd-gateway 将 Anthropic 原生格式转换为 OpenAI 兼容格式时，
# tool_use.input (dict) 被序列化为 function.arguments (JSON string)。
# 流式传输中偶发丢失最后一个 chunk，导致 JSON 缺少闭合括号。
# PydanticAI 内部重试时把截断的 args 原样放入对话历史，
# Bedrock 严格校验 tool_use.input 必须是 valid dict，直接 400 拒绝。
#
# 修复方式：patch ToolCallPart 的 args_as_dict/args_as_json_str，
# 在遇到截断 JSON 时自动补全闭合括号。
# ============================================================

def _try_fix_truncated_json(s: str) -> str | None:
    """尝试补全截断的 JSON 字符串（只补闭合括号/引号）"""
    if not s or not isinstance(s, str):
        return None
    s = s.rstrip()
    # 尝试逐步补全闭合字符
    for suffix in ['"}', '}', '"}]}', '"]}', ']}', ']']:
        candidate = s + suffix
        try:
            pydantic_core.from_json(candidate)
            return candidate
        except ValueError:
            continue
    return None


_original_args_as_dict = ToolCallPart.args_as_dict
_original_args_as_json_str = ToolCallPart.args_as_json_str


def _patched_args_as_dict(self, *, raise_if_invalid: bool = False):
    result = _original_args_as_dict(self, raise_if_invalid=False)
    # 检查是否返回了 INVALID_JSON 兜底
    if isinstance(result, dict) and len(result) == 1 and next(iter(result), None) == 'INVALID_JSON':
        raw = result.get('INVALID_JSON', '')
        fixed = _try_fix_truncated_json(raw)
        if fixed:
            try:
                import logging
                logging.getLogger(__name__).warning(
                    f"[ToolCallPart-Patch] 修复截断 JSON | tool={self.tool_name} "
                    f"original_len={len(raw)} fixed_suffix={fixed[len(raw):]}"
                )
                parsed = pydantic_core.from_json(fixed)
                if isinstance(parsed, dict):
                    self.args = parsed  # 同时修复原始 args，后续调用也受益
                    return parsed
            except (ValueError, AssertionError):
                pass
    return result


def _patched_args_as_json_str(self):
    if not self.args:
        return '{}'
    if isinstance(self.args, str):
        # 检查是否是有效 JSON
        try:
            pydantic_core.from_json(self.args)
            return self.args
        except ValueError:
            fixed = _try_fix_truncated_json(self.args)
            if fixed:
                import logging
                logging.getLogger(__name__).warning(
                    f"[ToolCallPart-Patch] 修复截断 JSON (json_str) | tool={self.tool_name} "
                    f"original_len={len(self.args)} fixed_suffix={fixed[len(self.args):]}"
                )
                self.args = fixed
                return fixed
            return self.args
    return pydantic_core.to_json(self.args).decode()


ToolCallPart.args_as_dict = _patched_args_as_dict
ToolCallPart.args_as_json_str = _patched_args_as_json_str

# 本地模块
from src.core.exceptions import OrchestrationTimeout, RoutingError
from src.core.logging import get_logger, session_id_var
from src.llm.config import get_model
from src.middleware.context import MiddlewareContext, TokenUsage
from src.middleware.pipeline import MiddlewarePipeline
from src.monitoring.pipeline_events import pipeline_step
from src.monitoring.trace_context import get_trace_id
from src.orchestrator.planner import plan_tasks
from src.orchestrator.prompts.system import build_system_prompt
from src.orchestrator.router import route_task
from src.schemas.agent import (
    ExecutionDAG,
    OrchestratorOutput,
    TaskNode,
    TaskStatus,
    WorkerResult,
)

logger = get_logger(__name__)

# 会话对话历史存储（内存实现）
_session_histories: Dict[str, list] = {}


# ============================================================
# 依赖注入容器
# ============================================================

@dataclass
class OrchestratorDeps:
    """Orchestrator 运行时依赖

    通过 PydanticAI 的依赖注入机制传入。
    """
    session_id: str = ""
    trace_id: str = ""
    workers: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    a2ui_frames: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# Orchestrator Agent
# ============================================================

def _dynamic_instructions(ctx: RunContext[OrchestratorDeps]) -> str:
    """动态构建 system prompt，注入 Skill 摘要和用户记忆"""
    from src.skills.registry import skill_registry
    skill_summary = skill_registry.get_skill_summary()
    # 用户记忆通过 query 前缀注入，此处仅传空占位
    return build_system_prompt(skill_summary=skill_summary)


orchestrator_agent = Agent(
    model=get_model("planning"),
    output_type=OrchestratorOutput,
    deps_type=OrchestratorDeps,
    instructions=_dynamic_instructions,
    name="Orchestrator",
    retries=2,
    instrument=InstrumentationSettings(version=1),
)

# Native tool 名称集合，用于在 event_stream_handler 中过滤，避免重复推送事件
_NATIVE_TOOL_NAMES = frozenset({
    "plan_and_decompose",
    "execute_native_worker",
    "execute_sandbox_task",
    "execute_skill",
    "list_available_skills",
    "create_new_skill",
    "emit_chart",
    "emit_widget",
    "search_skills",
    "recall_memory",
    "final_result",
})


# ============================================================
# Tool 定义
# ============================================================


async def _push_event(session_id: str, event: dict) -> None:
    """推送 A2UI 事件到 Redis Stream"""
    try:
        from src.streaming.stream_adapter import publish_event
        await publish_event(session_id, event)
    except Exception as e:
        logger.warning(f"[Orchestrator] 事件推送失败 | error={e}")


@orchestrator_agent.tool
async def plan_and_decompose(
    ctx: RunContext[OrchestratorDeps],
    query: str,
) -> Dict[str, Any]:
    """规划任务 DAG

    将用户请求拆解为结构化的子任务执行拓扑。

    Args:
        ctx: 运行上下文
        query: 用户自然语言请求

    Returns:
        DAG 序列化结果
    """
    sid = ctx.deps.session_id
    await _push_event(sid, {
        "event_type": "step",
        "step_id": "plan",
        "title": "规划任务",
        "status": "running",
    })

    async with pipeline_step("orchestrator.plan", session_id=sid) as ev:
        dag = await plan_tasks(query, ctx.deps.context)
        ev.add_metadata(task_count=len(dag.tasks) if hasattr(dag, 'tasks') else 0)

    await _push_event(sid, {
        "event_type": "step",
        "step_id": "plan",
        "title": "规划任务",
        "status": "completed",
    })

    return dag.model_dump()


@orchestrator_agent.tool
async def execute_native_worker(
    ctx: RunContext[OrchestratorDeps],
    task_id: str,
    task_type: str,
    description: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """执行可信子任务（Python 原生 Worker）

    在宿主环境安全执行 RAG 检索、数据库查询、API 调用等任务。

    Args:
        ctx: 运行上下文
        task_id: 任务 ID
        task_type: 任务类型
        description: 任务描述
        input_data: 任务输入

    Returns:
        Worker 执行结果
    """
    sid = ctx.deps.session_id
    # task_type → worker 名称映射
    WORKER_NAME_MAP = {
        "rag_retrieval": "rag_worker",
        "db_query": "db_query_worker",
        "api_call": "api_call_worker",
    }
    worker_name = WORKER_NAME_MAP.get(task_type, f"{task_type}_worker")
    step_id = f"worker-{task_id}"

    await _push_event(sid, {
        "event_type": "step",
        "step_id": step_id,
        "title": f"{description or task_type}",
        "status": "running",
    })

    worker = ctx.deps.workers.get(worker_name)

    if not worker:
        logger.warning(f"[Orchestrator] Worker 未注册 | worker={worker_name}")
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"{description or task_type}",
            "status": "failed",
            "detail": f"Worker '{worker_name}' 未注册",
        })
        return WorkerResult(
            task_id=task_id,
            success=False,
            error=f"Worker '{worker_name}' 未注册",
        ).model_dump()

    task = TaskNode(
        task_id=task_id,
        task_type=task_type,
        description=description,
        input_data=input_data,
    )

    try:
        async with pipeline_step(f"worker.native.{task_type}", metadata={
            "worker_type": worker_name, "task_id": task_id,
        }, session_id=sid) as ev:
            result = await worker.execute(task)
            ev.add_metadata(success=result.success)

        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"{description or task_type}",
            "status": "completed",
        })
        await _push_event(sid, {
            "event_type": "tool_result",
            "tool_type": "native_worker",
            "tool_name": task_type,
            "content": str(result.data) if result.data else "",
            "status": "success" if result.success else "failed",
        })

        return result.model_dump()
    except Exception as e:
        logger.error(
            f"[Orchestrator] Native Worker 执行失败 | "
            f"task_id={task_id} worker={worker_name} error={e}",
            exc_info=True,
        )
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"{description or task_type}",
            "status": "failed",
            "detail": str(e),
        })
        return WorkerResult(
            task_id=task_id,
            success=False,
            error=str(e),
        ).model_dump()


@orchestrator_agent.tool
async def execute_sandbox_task(
    ctx: RunContext[OrchestratorDeps],
    task_id: str,
    instruction: str,
    context_files: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """执行沙箱高危任务（E2B 隔离环境）

    在 E2B 沙箱中启动 Pi Agent 自主执行代码生成、脚本运行等高危任务。
    注意：如果此工具执行失败，请直接用 final_result 回答用户，不要重复调用。

    Args:
        ctx: 运行上下文
        task_id: 任务 ID
        instruction: 任务指令（建议控制在单一明确的任务，避免过于复杂）
        context_files: 需要注入沙箱的文件

    Returns:
        沙箱执行结果
    """
    sid = ctx.deps.session_id
    step_id = f"sandbox-{task_id}"

    # 防止同一 task_id 重复执行（Agent 循环调用保护）
    _sandbox_attempts_key = f"_sandbox_attempts_{task_id}"
    attempts = ctx.deps.context.get(_sandbox_attempts_key, 0)
    if attempts >= 2:
        logger.warning(
            f"[Orchestrator] 沙箱任务重试次数过多，终止 | "
            f"task_id={task_id} attempts={attempts}"
        )
        return WorkerResult(
            task_id=task_id,
            success=False,
            error=f"沙箱任务 '{task_id}' 已重试 {attempts} 次仍失败，请直接用已有信息回答用户。",
        ).model_dump()
    ctx.deps.context[_sandbox_attempts_key] = attempts + 1

    await _push_event(sid, {
        "event_type": "step",
        "step_id": step_id,
        "title": f"沙箱执行: {instruction[:30]}...",
        "status": "running",
    })

    sandbox_worker = ctx.deps.workers.get("sandbox_worker")

    if not sandbox_worker:
        logger.warning("[Orchestrator] 沙箱 Worker 未注册")
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"沙箱执行: {instruction[:30]}...",
            "status": "failed",
            "detail": "沙箱 Worker 未注册",
        })
        return WorkerResult(
            task_id=task_id,
            success=False,
            error="沙箱 Worker 未注册",
        ).model_dump()

    from src.schemas.sandbox import SandboxTask

    task = SandboxTask(
        task_id=task_id,
        instruction=instruction,
        context_files=context_files or {},
    )

    try:
        async with pipeline_step("worker.sandbox", metadata={
            "task_id": task_id,
        }, session_id=sid) as ev:
            result = await sandbox_worker.execute(task)
            ev.add_metadata(success=result.success)

        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"沙箱执行: {instruction[:30]}...",
            "status": "completed",
        })
        await _push_event(sid, {
            "event_type": "tool_result",
            "tool_type": "sandbox",
            "tool_name": f"sandbox-{task_id}",
            "content": result.final_answer if hasattr(result, "final_answer") and result.final_answer else str(result),
            "status": "success" if result.success else "failed",
        })

        return result.model_dump()
    except Exception as e:
        logger.error(
            f"[Orchestrator] 沙箱任务执行失败 | task_id={task_id} error={e}",
            exc_info=True,
        )
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"沙箱执行: {instruction[:30]}...",
            "status": "failed",
            "detail": str(e),
        })
        return WorkerResult(
            task_id=task_id,
            success=False,
            error=str(e),
        ).model_dump()


@orchestrator_agent.tool
async def execute_skill(
    ctx: RunContext[OrchestratorDeps],
    skill_name: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """执行已注册的 Skill

    调用 skill/ 目录下已注册的 Skill 脚本，如论文搜索、专利检索等。

    Args:
        ctx: 运行上下文
        skill_name: Skill 名称（如 baidu-search、ai-ppt-generator）
        params: 传给脚本的参数字典，会被序列化为 JSON 作为脚本第一个参数。
                例如 baidu-search 需要 {"query": "搜索词"}

    Returns:
        Skill 执行结果
    """
    sid = ctx.deps.session_id
    step_id = f"skill-{skill_name}-{id(params) % 10000}"

    await _push_event(sid, {
        "event_type": "step",
        "step_id": step_id,
        "title": f"调用 {skill_name}",
        "status": "running",
    })

    from src.skills.executor import collect_skill_files
    from src.skills.registry import skill_registry
    from src.schemas.sandbox import SandboxTask

    logger.info(
        f"[Orchestrator] 执行 Skill（沙箱模式）| skill={skill_name} params={params}"
    )

    # 沙箱重试保护
    _attempts_key = f"_skill_attempts_{skill_name}"
    attempts = ctx.deps.context.get(_attempts_key, 0)
    if attempts >= 2:
        logger.warning(f"[Orchestrator] Skill 沙箱重试次数过多，终止 | skill={skill_name}")
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"调用 {skill_name}",
            "status": "failed",
            "detail": f"已重试 {attempts} 次仍失败",
        })
        return {"skill_name": skill_name, "success": False, "stdout": "",
                "stderr": f"Skill '{skill_name}' 已重试 {attempts} 次仍失败，请直接用已有信息回答用户。",
                "exit_code": 1, "output_data": None}
    ctx.deps.context[_attempts_key] = attempts + 1

    # 获取 skill 信息
    skill_info = skill_registry.get(skill_name)
    if not skill_info:
        await _push_event(sid, {"event_type": "step", "step_id": step_id,
                                "title": f"调用 {skill_name}", "status": "failed"})
        return {"skill_name": skill_name, "success": False, "stdout": "",
                "stderr": f"Skill '{skill_name}' 未注册", "exit_code": 1, "output_data": None}

    # 收集 skill 文件注入沙箱
    context_files = collect_skill_files(skill_info)

    # 构建所有可用脚本的完整命令
    injected_scripts = sorted(k for k in context_files if k.startswith("scripts/") and k.endswith(".py"))
    params_json = json.dumps(params, ensure_ascii=False)
    quoted_params = shlex.quote(params_json)

    if len(injected_scripts) == 1:
        # 单脚本：直接执行，不给 LLM 推断空间
        exec_command = f"python3 {injected_scripts[0]} {quoted_params}"
        instruction = (
            f"脚本文件已注入到当前工作目录。\n\n"
            f"## 执行命令（直接运行，不要修改路径）\n"
            f"```bash\n{exec_command}\n```\n\n"
            f"用 bash 工具执行上方命令，输出结果。"
        )
    else:
        # 多脚本：列出所有可用命令，让 LLM 根据文档和参数选择
        doc_content = skill_info.doc_content or ""
        commands_list = "\n".join(
            f"- `python3 {s} {quoted_params}`" for s in injected_scripts
        )
        instruction = (
            f"脚本文件已注入到当前工作目录。\n\n"
            f"## Skill 文档\n{doc_content}\n\n"
            f"## 可用命令（只能从以下命令中选择，不要自行拼接路径）\n{commands_list}\n\n"
            f"## 执行参数\n{params_json}\n\n"
            f"根据参数和文档选择正确的命令，用 bash 工具执行，输出结果。"
        )

    sandbox_worker = ctx.deps.workers.get("sandbox_worker")
    if not sandbox_worker:
        await _push_event(sid, {"event_type": "step", "step_id": step_id,
                                "title": f"调用 {skill_name}", "status": "failed"})
        return {"skill_name": skill_name, "success": False, "stdout": "",
                "stderr": "沙箱 Worker 未注册", "exit_code": 1, "output_data": None}

    task = SandboxTask(
        task_id=f"skill-{skill_name}-{id(params) % 10000}",
        instruction=instruction,
        context_files=context_files,
        timeout=300,
    )

    try:
        async with pipeline_step(f"skill.execute.{skill_name.replace('-', '_')}", metadata={
            "skill_name": skill_name,
        }, session_id=sid) as ev:
            result = await sandbox_worker.execute(task)
            ev.add_metadata(success=result.success)

        output = result.final_answer if hasattr(result, "final_answer") and result.final_answer else str(result)

        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"调用 {skill_name}",
            "status": "completed" if result.success else "failed",
        })
        await _push_event(sid, {
            "event_type": "tool_result",
            "tool_type": "skill",
            "tool_name": skill_name,
            "content": output,
            "status": "success" if result.success else "failed",
        })

        return {
            "skill_name": skill_name,
            "success": result.success,
            "stdout": output,
            "stderr": result.error if hasattr(result, "error") else "",
            "exit_code": 0 if result.success else 1,
            "output_data": None,
        }
    except Exception as e:
        logger.error(f"[Orchestrator] Skill 执行失败 | skill={skill_name} error={e}", exc_info=True)
        await _push_event(sid, {
            "event_type": "step",
            "step_id": step_id,
            "title": f"调用 {skill_name}",
            "status": "failed",
            "detail": str(e),
        })
        return {"skill_name": skill_name, "success": False, "stdout": "", "stderr": str(e), "exit_code": 1, "output_data": None}


@orchestrator_agent.tool
async def list_available_skills(
    ctx: RunContext[OrchestratorDeps],
) -> Dict[str, Any]:
    """列出所有可用的 Skill

    返回已注册的 Skill 列表及其描述，帮助决定使用哪个 Skill。

    Returns:
        Skill 列表
    """
    from src.skills.registry import skill_registry

    skills = skill_registry.list_skills()
    return {
        "skills": [
            {
                "name": s.metadata.name,
                "description": s.metadata.description,
                "scripts": s.scripts,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@orchestrator_agent.tool
async def create_new_skill(
    ctx: RunContext[OrchestratorDeps],
    name: str,
    description: str,
    script_name: str = "main.py",
    script_content: str = "",
    doc_content: str = "",
) -> Dict[str, Any]:
    """创建新的 Skill

    根据用户需求动态创建一个新的 Skill，包含标准目录结构（SKILL.md + scripts/）。
    如果不提供 script_content，会自动生成模板脚本。

    Args:
        ctx: 运行上下文
        name: Skill 名称（小写字母+连字符，如 code-optimizer）
        description: Skill 功能描述
        script_name: 主脚本文件名（默认 main.py）
        script_content: 脚本源代码（可选，不传则自动生成模板）
        doc_content: 额外的使用文档内容（可选）

    Returns:
        创建结果
    """
    from src.skills.creator import create_skill
    from src.skills.schema import SkillCreateRequest

    # 自动规范化名称：转小写、空格/下划线转连字符、去除非法字符
    import re
    normalized_name = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    normalized_name = re.sub(r'-+', '-', normalized_name).strip('-')
    if not normalized_name:
        normalized_name = "custom-skill"

    logger.info(f"[Orchestrator] 创建 Skill | name={normalized_name} (原始: {name})")

    try:
        request = SkillCreateRequest(
            name=normalized_name,
            description=description,
            script_name=script_name,
            script_content=script_content,
            doc_content=doc_content,
        )
        info = await create_skill(request)
        return {
            "success": True,
            "name": info.metadata.name,
            "description": info.metadata.description,
            "scripts": info.scripts,
            "message": f"Skill '{name}' 创建成功",
        }
    except Exception as e:
        logger.error(f"[Orchestrator] Skill 创建失败 | name={name} error={e}")
        return {
            "success": False,
            "error": str(e),
        }


@orchestrator_agent.tool
async def emit_chart(
    ctx: RunContext[OrchestratorDeps],
    title: str,
    chart_type: str,
    x_axis: List[str],
    series_data: str,
) -> Dict[str, Any]:
    """渲染数据图表到前端（折线图、柱状图、饼图、散点图）

    当需要展示数据可视化时，必须调用此工具，而不是用文字描述图表。
    前端会使用 ECharts 渲染交互式图表。

    Args:
        ctx: 运行上下文
        title: 图表标题
        chart_type: 图表类型，可选值：line / bar / pie / scatter
        x_axis: X 轴标签列表，如 ["1月", "2月", "3月"]
        series_data: 数据系列的 JSON 字符串。简单场景传数字数组如 "[100, 200, 300]"；
                     多系列传对象数组如 '[{"name": "系列A", "data": [1,2,3]}]'

    Returns:
        渲染确认
    """
    import json as _json
    try:
        parsed_series = _json.loads(series_data)
    except Exception:
        parsed_series = series_data

    widget_id = f"chart-{uuid.uuid4().hex[:8]}"
    frame = {
        "event_type": "render_widget",
        "widget_id": widget_id,
        "ui_component": "DataChart",
        "props": {
            "title": title,
            "chartType": chart_type,
            "xAxis": x_axis,
            "seriesData": parsed_series,
        },
        "trace_id": ctx.deps.trace_id,
    }
    ctx.deps.a2ui_frames.append(frame)
    await _push_event(ctx.deps.session_id, frame)
    logger.info(f"[Orchestrator] emit_chart | widget_id={widget_id} type={chart_type}")
    return {"success": True, "widget_id": widget_id}


@orchestrator_agent.tool
async def emit_widget(
    ctx: RunContext[OrchestratorDeps],
    ui_component: str,
    props: Dict[str, Any],
) -> Dict[str, Any]:
    """渲染任意前端组件

    支持的组件：DataChart, ArtifactPreview, TerminalView, ProcessUI。
    对于图表类需求，优先使用 emit_chart 工具（参数更明确）。

    各组件 props 格式（必须严格遵守）：
    - ArtifactPreview: {"code": "源代码内容", "language": "python", "title": "文件名"}
    - TerminalView: {"lines": ["命令1", "输出1"], "title": "终端标题"}

    Args:
        ctx: 运行上下文
        ui_component: 前端组件名称
        props: 组件 props

    Returns:
        渲染确认
    """
    widget_id = f"widget-{uuid.uuid4().hex[:8]}"
    frame = {
        "event_type": "render_widget",
        "widget_id": widget_id,
        "ui_component": ui_component,
        "props": props,
        "trace_id": ctx.deps.trace_id,
    }
    ctx.deps.a2ui_frames.append(frame)
    await _push_event(ctx.deps.session_id, frame)
    logger.info(f"[Orchestrator] emit_widget | widget_id={widget_id} component={ui_component} props={props}")
    return {"success": True, "widget_id": widget_id}


@orchestrator_agent.tool
async def search_skills(
    ctx: RunContext[OrchestratorDeps],
    query: str,
) -> Dict[str, Any]:
    """按关键词检索匹配的 Skill，返回完整定义

    当 system prompt 中的 Skill 摘要不够详细时，使用此工具获取完整的 Skill 定义。

    Args:
        ctx: 运行上下文
        query: 搜索关键词（如 "ppt"、"搜索"、"论文"）

    Returns:
        匹配的 Skill 列表（含完整 doc_content）
    """
    from src.skills.registry import skill_registry

    results = skill_registry.search_skills(query)
    return {
        "skills": [
            {
                "name": s.metadata.name,
                "description": s.metadata.description,
                "scripts": s.scripts,
                "doc_content": s.doc_content,
            }
            for s in results
        ],
        "total": len(results),
        "query": query,
    }


@orchestrator_agent.tool
async def recall_memory(
    ctx: RunContext[OrchestratorDeps],
    user_id: str,
) -> Dict[str, Any]:
    """检索用户历史记忆

    获取用户的画像信息和历史事实，帮助理解用户背景。

    Args:
        ctx: 运行上下文
        user_id: 用户 ID

    Returns:
        用户记忆数据
    """
    from src.memory.retriever import get_memory_retriever

    retriever = get_memory_retriever()
    memory_text = await retriever.retrieve(user_id)
    return {
        "user_id": user_id,
        "memory": memory_text if memory_text else "无历史记忆",
        "has_memory": bool(memory_text),
    }


# ============================================================
# 编排入口
# ============================================================

async def run_orchestrator(
    query: str,
    session_id: Optional[str] = None,
    workers: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    user_id: str = "default",
    mode: str = "auto",
) -> AsyncGenerator[str, None]:
    """运行编排器 — 三阶段管道：Classify → Assemble → Execute

    Args:
        query: 用户请求
        session_id: 会话 ID
        workers: 已注册的 Worker 实例
        context: 附加上下文
        user_id: 用户 ID（用于记忆检索）
        mode: 执行模式 (auto/direct/plan_and_execute)

    Yields:
        str: answer token

    Raises:
        OrchestrationTimeout: 编排超时
    """
    sid = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    trace_id = get_trace_id()

    deps = OrchestratorDeps(
        session_id=sid,
        trace_id=trace_id,
        workers=workers or {},
        context=context or {},
    )

    logger.info(
        f"[Orchestrator] 开始编排 | "
        f"session_id={sid} trace_id={trace_id} mode={mode} query_len={len(query)}"
    )

    try:
        # 获取会话历史
        history = _session_histories.get(sid, [])

        # 注入用户记忆
        memory_text = await _retrieve_user_memory(user_id)

        await _push_event(sid, {"event_type": "thinking", "content": "理解意图，分类请求类型...\n"})

        # ── Stage 1: Classify ──
        from src.orchestrator.intent_router import intent_router
        async with pipeline_step("intent.classify", session_id=sid) as ev:
            execution_mode = intent_router.classify(query, mode)
            ev.add_metadata(execution_mode=execution_mode.value)

        # ── Stage 2: Assemble ──
        from src.orchestrator.toolset_assembler import toolset_assembler
        await _push_event(sid, {"event_type": "thinking", "content": f"模式: {execution_mode.value}，装配工具集...\n"})
        async with pipeline_step("toolset.assemble", session_id=sid):
            assemble_result = toolset_assembler.assemble(execution_mode)

        # ── Stage 3: Execute (wrapped by middleware pipeline) ──
        await _push_event(sid, {"event_type": "thinking", "content": "开始执行任务...\n"})
        pipeline = _build_middleware_pipeline()
        mw_context = MiddlewareContext(
            session_id=sid,
            trace_id=trace_id,
            messages=list(history) if history else [],
        )

        async def _agent_fn(ctx: MiddlewareContext) -> OrchestratorOutput:
            return await _execute_agent(
                ctx=ctx,
                query=query,
                memory_text=memory_text,
                deps=deps,
                assemble_result=assemble_result,
            )

        try:
            if pipeline:
                output = await pipeline.execute(mw_context, _agent_fn)
            else:
                output = await _agent_fn(mw_context)
        except (Exception, BaseExceptionGroup) as agent_err:
            # Agent 执行失败（如 final_result JSON 截断 → Bedrock 400）
            # 尝试从已有的 tool results 中提取内容，走 fallback 汇总
            logger.warning(
                f"[Orchestrator] Agent 执行失败，尝试 fallback 汇总 | "
                f"session_id={sid} error={agent_err}"
            )
            all_messages = _session_histories.get(sid, [])
            tool_contents = _extract_tool_results(all_messages)
            # 如果历史已被清空，尝试从 deps 中恢复保留的 tool results
            if not tool_contents:
                tool_contents = deps.context.get("_fallback_tool_results", "")
            if tool_contents:
                logger.info(f"[Orchestrator] 启动 fallback 流式汇总 | tool_content_len={len(tool_contents)}")
                async for token in _summarize_tool_results_stream(query, tool_contents):
                    yield token
                return
            # 没有可用的 tool results，重新抛出
            raise

        logger.info(
            f"[Orchestrator] 编排完成 | "
            f"session_id={sid} mode={execution_mode.value} "
            f"worker_results={len(output.worker_results)} "
            f"history_len={len(_session_histories.get(sid, []))}"
        )

        # 构建 answer：优先用结构化输出的 answer 字段
        answer = output.answer if output.answer and output.answer.strip() else ""

        # Fallback 1：从 worker_results 汇总
        if not answer and output.worker_results:
            parts = [str(wr.data) for wr in output.worker_results if wr.success and wr.data]
            if parts:
                answer = "\n\n".join(parts)

        # Fallback 2：用流式 LLM 汇总 tool 返回内容
        if not answer:
            all_messages = _session_histories.get(sid, [])
            tool_contents = _extract_tool_results(all_messages)
            # 如果历史已被清空，尝试从 deps 中恢复保留的 tool results
            if not tool_contents:
                tool_contents = deps.context.get("_fallback_tool_results", "")
            if tool_contents:
                logger.info(f"[Orchestrator] answer 为空，启动流式汇总 | tool_content_len={len(tool_contents)}")
                async for token in _summarize_tool_results_stream(query, tool_contents):
                    yield token
                return

        if answer:
            yield answer

    except asyncio.TimeoutError as e:
        raise OrchestrationTimeout(
            "编排超时",
            trace_id=trace_id,
            context={"session_id": sid, "query": query[:200]},
        ) from e


# ============================================================
# 消息历史清洗与 fallback 辅助函数
# ============================================================

def _sanitize_message_history(messages: list) -> list:
    """清洗对话历史中残缺的 tool_use.input

    Bedrock 严格校验 tool_use.input 必须是 valid dict，
    但 LLM 偶发返回截断的 JSON 会导致 input 为字符串或 None。
    遍历历史消息，将非 dict 的 tool_use.input 替换为空 dict。
    """
    for msg in messages:
        if not hasattr(msg, 'parts'):
            continue
        for part in msg.parts:
            # PydanticAI ToolCallPart 的 args 字段对应 tool_use.input
            if hasattr(part, 'args') and not isinstance(part.args, dict):
                logger.warning(
                    f"[Orchestrator] 清洗残缺 tool_use.input | "
                    f"tool={getattr(part, 'tool_name', '?')} "
                    f"original_type={type(part.args).__name__}"
                )
                part.args = {}
    return messages


def _preserve_tool_results_for_fallback(messages: list, deps: OrchestratorDeps) -> None:
    """清空历史前保留 tool results，确保 fallback 汇总有数据可用"""
    tool_contents = _extract_tool_results(messages)
    if tool_contents:
        deps.context["_fallback_tool_results"] = tool_contents
        logger.info(
            f"[Orchestrator] 保留 tool results 用于 fallback | count={len(tool_contents)}"
        )


def _dump_tool_call_args(messages: list, error: BaseException) -> None:
    """诊断日志：打印对话历史中所有 tool call 的原始 args，用于排查截断问题"""
    logger.error(f"[Orchestrator] Agent 调用失败，开始诊断 tool call args | error_type={type(error).__name__}")
    for i, msg in enumerate(messages):
        if not hasattr(msg, 'parts'):
            continue
        for part in msg.parts:
            if hasattr(part, 'tool_name') and hasattr(part, 'args'):
                args = part.args
                args_type = type(args).__name__
                args_preview = str(args)[:500] if args else "<None>"
                # 检查 JSON 是否完整
                is_valid = False
                if isinstance(args, dict):
                    is_valid = True
                elif isinstance(args, str):
                    try:
                        import json
                        json.loads(args)
                        is_valid = True
                    except (json.JSONDecodeError, ValueError):
                        pass
                logger.error(
                    f"[Orchestrator] 诊断 tool_call | "
                    f"msg_index={i} tool={part.tool_name} "
                    f"args_type={args_type} valid_json={is_valid} "
                    f"args_len={len(str(args)) if args else 0} "
                    f"args={args_preview}"
                )


# ============================================================
# 统一 Agent 执行函数
# ============================================================

async def _execute_agent(
    ctx: MiddlewareContext,
    query: str,
    memory_text: str,
    deps: OrchestratorDeps,
    assemble_result: Any,
) -> OrchestratorOutput:
    """统一 Agent 执行函数

    处理所有模式的公共逻辑：MCP fallback、工具过滤、prompt_prefix 注入、
    token usage 更新、A2UI 帧注入、历史保存。

    Args:
        ctx: middleware 上下文
        query: 用户原始请求
        memory_text: 用户记忆文本
        deps: Orchestrator 依赖
        assemble_result: ToolSetAssembler 的装配结果
    """
    # 构建 effective query
    effective_query = query
    if assemble_result.prompt_prefix:
        effective_query = assemble_result.prompt_prefix + effective_query
    if memory_text:
        effective_query = f"{effective_query}\n\n{memory_text}"

    # 选择 Agent 实例（direct 模式可能使用独立 Agent）
    agent = assemble_result.agent_override or orchestrator_agent

    # 加载 MCP toolsets
    toolsets = _get_mcp_toolsets()

    # MCP 工具事件处理器：拦截 FunctionToolCallEvent / FunctionToolResultEvent
    # 只推送 MCP 工具事件，跳过 native tool（已在各自工具函数内推送）
    async def _mcp_event_handler(run_ctx: Any, events: Any) -> None:
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                tool_name = event.part.tool_name
                if tool_name not in _NATIVE_TOOL_NAMES:
                    await _push_event(deps.session_id, {
                        "event_type": "tool_call",
                        "tool_type": "mcp",
                        "tool_name": tool_name,
                    })
            elif isinstance(event, FunctionToolResultEvent):
                tool_name = event.result.tool_name
                if tool_name not in _NATIVE_TOOL_NAMES:
                    content = event.result.content
                    outcome = getattr(event.result, 'outcome', 'success')
                    await _push_event(deps.session_id, {
                        "event_type": "tool_result",
                        "tool_type": "mcp",
                        "tool_name": tool_name,
                        "content": str(content),
                        "status": "success" if outcome == "success" else "failed",
                    })

    def _is_invalid_tool_input_error(err: BaseException) -> bool:
        """检测 Bedrock tool_use.input 格式错误（历史消息中含残缺 tool call）"""
        def _matches(e: BaseException) -> bool:
            s = str(e)
            # Bedrock 严格校验 tool_use.input 必须是 valid dict
            if "tool_use.input" in s and "valid dictionary" in s:
                return True
            # PydanticAI JSON 解析错误（LLM 返回截断的 tool call JSON）
            if "json_invalid" in s and "EOF while parsing" in s:
                return True
            return False

        if _matches(err):
            return True
        # 检查异常链
        if err.__cause__ and _matches(err.__cause__):
            return True
        if err.__context__ and _matches(err.__context__):
            return True
        # 检查 ExceptionGroup 的子异常
        if isinstance(err, BaseExceptionGroup):
            return any(_is_invalid_tool_input_error(e) for e in err.exceptions)
        return False

    # 执行 Agent（带 MCP fallback）
    async with pipeline_step("orchestrator.execute", session_id=deps.session_id) as ev:
        try:
            result = await agent.run(
                effective_query,
                deps=deps,
                message_history=_sanitize_message_history(ctx.messages) if ctx.messages else None,
                toolsets=toolsets if toolsets else None,
                event_stream_handler=_mcp_event_handler,
            )
        except (Exception, BaseExceptionGroup) as mcp_err:
            # 诊断日志：打印对话历史中所有 tool call 的原始 args
            _dump_tool_call_args(ctx.messages, mcp_err)

            if _is_invalid_tool_input_error(mcp_err):
                # 历史消息中含残缺 tool_use，保留 tool results 后清空历史重试
                logger.warning(
                    f"[Orchestrator] 检测到残缺 tool_use 历史，清空历史重试 | error={mcp_err}"
                )
                _preserve_tool_results_for_fallback(ctx.messages, deps)
                ctx.messages = []
                _session_histories.pop(deps.session_id, None)
                result = await agent.run(
                    effective_query,
                    deps=deps,
                    message_history=None,
                    toolsets=toolsets if toolsets else None,
                    event_stream_handler=_mcp_event_handler,
                )
            elif toolsets:
                logger.warning(
                    f"[Orchestrator] MCP 连接失败，降级为无 MCP 模式 | error={mcp_err}"
                )
                try:
                    result = await agent.run(
                        effective_query,
                        deps=deps,
                        message_history=_sanitize_message_history(ctx.messages) if ctx.messages else None,
                        event_stream_handler=_mcp_event_handler,
                    )
                except (Exception, BaseExceptionGroup) as fallback_err:
                    if _is_invalid_tool_input_error(fallback_err):
                        logger.warning(
                            f"[Orchestrator] MCP 降级后仍检测到残缺 tool_use 历史，清空历史重试 | error={fallback_err}"
                        )
                        _preserve_tool_results_for_fallback(ctx.messages, deps)
                        ctx.messages = []
                        _session_histories.pop(deps.session_id, None)
                        result = await agent.run(
                            effective_query,
                            deps=deps,
                            message_history=None,
                            event_stream_handler=_mcp_event_handler,
                        )
                    else:
                        raise
            else:
                raise

    # 更新 token usage
    if hasattr(result, 'usage') and result.usage:
        ctx.token_usage.input_tokens = getattr(result.usage, 'input_tokens', 0) or 0
        ctx.token_usage.output_tokens = getattr(result.usage, 'output_tokens', 0) or 0
        ctx.token_usage.total_tokens = getattr(result.usage, 'total_tokens', 0) or 0

    output = result.output

    # 注入 A2UI 帧
    if deps.a2ui_frames:
        output.a2ui_frames = deps.a2ui_frames

    # 保存对话历史
    _session_histories[deps.session_id] = result.all_messages()
    ctx.messages = result.all_messages()

    return output


async def _retrieve_user_memory(user_id: str) -> str:
    """检索用户记忆，失败时静默返回空"""
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        if not settings.memory.enabled:
            return ""

        from src.memory.retriever import get_memory_retriever
        retriever = get_memory_retriever()
        return await retriever.retrieve(user_id)
    except Exception as e:
        logger.warning(f"[Orchestrator] 记忆检索失败 | user_id={user_id} error={e}")
        return ""


def _build_middleware_pipeline() -> Optional[MiddlewarePipeline]:
    """根据配置构建 middleware pipeline"""
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        if not settings.middleware.enabled:
            return None

        from src.middleware.memory_mw import MemoryMiddleware
        from src.middleware.summarization import SummarizationMiddleware

        middlewares = [
            SummarizationMiddleware(
                threshold_ratio=settings.middleware.summarization_threshold_ratio,
            ),
            MemoryMiddleware(),
        ]

        return MiddlewarePipeline(middlewares)
    except Exception as e:
        logger.warning(f"[Orchestrator] Middleware pipeline 构建失败 | error={e}")
        return None


async def _summarize_tool_results_stream(query: str, tool_contents: str) -> AsyncGenerator[str, None]:
    """用快速模型流式汇总 tool 返回内容，逐 token yield"""
    try:
        from pydantic_ai import Agent

        summarizer = Agent(
            model=get_model("fast"),
            output_type=str,
            instructions="""你是一个信息汇总助手。根据用户的原始问题和工具返回的原始数据，生成一份结构化、有价值的回答。

要求：
- 直接回答用户的问题，不要提及"工具"或"搜索结果"
- 使用 Markdown 格式，包含标题、列表、表格等
- 提炼关键信息，去除冗余
- 如果数据包含论文/文献，整理成结构化列表
- 语言与用户问题保持一致""",
        )

        prompt = f"用户问题：{query}\n\n以下是收集到的相关信息：\n\n{tool_contents[:6000]}"
        async with summarizer.run_stream(prompt) as stream:
            async for token in stream.stream_text(delta=True):
                if token:
                    yield token
    except Exception as e:
        logger.warning(f"[Orchestrator] 流式汇总失败，使用原始内容 | error={e}")
        yield tool_contents[:3000]


def _extract_tool_results(messages: list) -> str:
    """从 PydanticAI 对话历史中提取 tool 返回内容作为 fallback answer

    当 LLM 没有在 final_result.answer 中填充内容时，
    从 skill/worker 的 tool 返回中提取 stdout 原样返回。
    """
    import json

    skip_tools = {"list_available_skills", "create_new_skill", "plan_and_decompose"}
    parts = []

    for msg in messages:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "content") and hasattr(part, "tool_name"):
                    if part.tool_name in skip_tools:
                        continue
                    content = str(part.content)

                    # 跳过 MCP validation errors
                    if "validation error" in content.lower() and "Field required" in content:
                        continue

                    # 尝试从 skill JSON 中提取 stdout
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            if data.get("stdout"):
                                content = data["stdout"]
                            elif data.get("success") is False:
                                continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                    if len(content.strip()) > 20:
                        parts.append(content.strip())

        elif isinstance(msg, dict) and msg.get("role") == "tool":
            content = msg.get("content", "")
            if "validation error" in content.lower() and "Field required" in content:
                continue
            try:
                data = json.loads(content)
                if isinstance(data, dict) and data.get("stdout"):
                    content = data["stdout"]
            except (json.JSONDecodeError, TypeError):
                pass
            if len(content.strip()) > 20:
                parts.append(content.strip())

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)


def _get_mcp_toolsets() -> list:
    """获取 MCP toolsets 列表"""
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        if not settings.mcp.is_configured:
            return []

        from src.mcp.client import create_mcp_servers_from_config
        return create_mcp_servers_from_config()
    except Exception as e:
        logger.warning(f"[Orchestrator] MCP toolsets 加载失败 | error={e}")
        return []
