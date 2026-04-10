"""REST API 网关

POST /api/agent/query — 提交查询
GET /api/agent/stream/{session_id} — SSE 事件流
"""

from __future__ import annotations

import importlib
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src_deepagent.core.logging import get_logger, session_id_var, trace_id_var
from src_deepagent.orchestrator.agent_factory import create_orchestrator_agent
from src_deepagent.orchestrator.reasoning_engine import (
    ExecutionMode,
    ReasoningEngine,
    escalate_plan,
)
from src_deepagent.schemas.agent import OrchestratorOutput, SessionStatus
from src_deepagent.schemas.api import QueryRequest, QueryResponse
from src_deepagent.state.session_manager import SessionManager
from src_deepagent.streaming.sse_endpoint import sse_event_generator
from src_deepagent.streaming.stream_adapter import StreamAdapter
from src_deepagent.agents.factory import create_sub_agent_configs

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# ── Worker 注册表 ────────────────────────────────────────

_WORKER_REGISTRY: dict[str, tuple[str, str]] = {
    "sandbox_worker": ("src_deepagent.workers.sandbox.sandbox_worker", "SandboxWorker"),
    # "rag_worker": ("src_deepagent.workers.native.rag_worker", "RAGWorker"),  # TODO: 缺少 embedding 环节，暂不可用
    "db_query_worker": ("src_deepagent.workers.native.db_query_worker", "DBQueryWorker"),
    "api_call_worker": ("src_deepagent.workers.native.api_call_worker", "APICallWorker"),
}


def init_workers() -> dict[str, Any]:
    """初始化所有 Worker（懒加载，跳过不可用的）"""
    workers: dict[str, Any] = {}
    for name, (module_path, class_name) in _WORKER_REGISTRY.items():
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            workers[name] = cls()
            logger.info(f"Worker 初始化成功 | name={name}")
        except Exception as e:
            logger.warning(f"Worker 初始化跳过 | name={name} error={e}")
    return workers


# ── 全局状态（由 lifespan 初始化） ───────────────────────

_workers: dict[str, Any] = {}
_reasoning_engine: ReasoningEngine | None = None
_session_manager: SessionManager | None = None
_stream_adapter: StreamAdapter | None = None


def configure(
    workers: dict[str, Any],
    redis_client: Any = None,
) -> None:
    """配置网关全局状态（由 main.py lifespan 调用）"""
    global _workers, _reasoning_engine, _session_manager, _stream_adapter  # noqa: PLW0603
    _workers = workers
    _reasoning_engine = ReasoningEngine(workers=workers)
    _session_manager = SessionManager(redis_client=redis_client)
    if redis_client:
        _stream_adapter = StreamAdapter(redis_client=redis_client)


# ── 端点 ──────────────────────────────────────────────────


@router.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest) -> QueryResponse:
    """提交用户查询"""
    if not _reasoning_engine:
        return QueryResponse(success=False, session_id="", trace_id="", message="服务未初始化")

    # 生成 ID
    sid = request.session_id or f"s-{uuid.uuid4().hex[:12]}"
    tid = f"t-{uuid.uuid4().hex[:12]}"

    # 注入上下文变量
    session_id_var.set(sid)
    trace_id_var.set(tid)

    logger.info(f"收到查询 | query={request.query[:100]} mode={request.mode}")

    # 创建会话
    if _session_manager:
        await _session_manager.create(sid, tid, request.query)

    # 异步执行编排
    import asyncio

    asyncio.create_task(_run_orchestration(sid, tid, request))

    return QueryResponse(
        success=True,
        session_id=sid,
        trace_id=tid,
        message="查询已提交，请通过 SSE 获取结果",
    )


@router.get("/stream/{session_id}")
async def stream_events(session_id: str, request: Request) -> StreamingResponse:
    """SSE 事件流端点"""
    last_event_id = request.headers.get("Last-Event-ID", "0-0")

    if not _stream_adapter:
        async def empty_gen():
            yield "event: error\ndata: {\"error\": \"Stream 未初始化\"}\n\n"
        return StreamingResponse(empty_gen(), media_type="text/event-stream")

    return StreamingResponse(
        sse_event_generator(_stream_adapter, session_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 编排执行 ─────────────────────────────────────────────


def _needs_escalation(result: Any, plan: Any) -> bool:
    """判断 DIRECT 模式结果是否需要升级到 AUTO

    升级条件（满足任一）：
    - Agent 执行异常（result 为 None）
    - 输出为空或过短（LLM 无法直接回答）
    - 输出开头包含明确的自述无法完成的文本

    注意：只检查输出前 200 字符（Agent 自述区域），避免在长内容中误匹配。
    """
    if plan.mode != ExecutionMode.DIRECT:
        return False

    if plan.escalated_from is not None:
        # 已经是升级后的计划，不再二次升级
        return False

    from src_deepagent.config.settings import get_settings

    if not get_settings().reasoning.escalation_enabled:
        return False

    if result is None:
        return True

    output = result.output if hasattr(result, "output") else str(result)
    answer = output if isinstance(output, str) else (
        output.answer if hasattr(output, "answer") else str(output)
    )

    # 空输出
    if not answer or not answer.strip():
        return True

    # 只检查开头 200 字符，避免在搜索结果等长内容中误匹配
    head = answer.strip()[:200]

    # Agent 明确自述无法完成（排除"需要搜索/需要查询"等常见内容描述词）
    _ESCALATION_SIGNALS = (
        "无法直接回答", "无法完成", "我无法", "无法回答",
        "需要使用工具", "需要调用工具",
        "I cannot directly", "I don't have access",
        "I'm unable to", "I need to use tools",
    )
    return any(signal in head for signal in _ESCALATION_SIGNALS)


def _extract_last_text(run: Any) -> str:
    """从 agent iter run 的消息历史中提取最后一条文本回答"""
    try:
        for msg in reversed(run.all_messages()):
            if hasattr(msg, "parts"):
                for part in reversed(msg.parts):
                    if hasattr(part, "content") and isinstance(part.content, str) and part.content.strip():
                        return part.content.strip()
    except Exception:
        pass
    return ""


async def _execute_plan(
    plan: Any,
    request: QueryRequest,
    session_id: str,
    trace_id: str,
) -> Any:
    """执行单次编排计划，流式推送中间事件，返回 agent result"""
    from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode, End
    from pydantic_ai.usage import UsageLimits
    from src_deepagent.orchestrator.reasoning_engine import ExecutionMode

    # 只有 AUTO 和 SUB_AGENT 模式才需要 Sub-Agent 配置
    # DIRECT 和 PLAN_AND_EXECUTE 模式下隐藏 task() 工具，避免误调
    if plan.mode in (ExecutionMode.AUTO, ExecutionMode.SUB_AGENT):
        sub_agent_configs = create_sub_agent_configs(plan.resources.agent_tools)
    else:
        sub_agent_configs = []

    agent, deps = create_orchestrator_agent(
        plan=plan,
        sub_agent_configs=sub_agent_configs,
        session_id=session_id,
        trace_id=trace_id,
        publish_fn=_publish,
    )

    effective_query = plan.prompt_prefix + request.query

    try:
        async with agent.iter(
            effective_query,
            deps=deps,
            usage_limits=UsageLimits(request_limit=15),
        ) as run:
            async for node in run:
                if isinstance(node, CallToolsNode):
                    # 推送工具调用事件
                    for part in node.model_response.parts:
                        if hasattr(part, "tool_name"):
                            await _publish(session_id, {
                                "event_type": "tool_call",
                                "tool_name": part.tool_name,
                                "args": str(part.args)[:200] if hasattr(part, "args") else "",
                            })
                elif isinstance(node, End):
                    break

            result = run.result
    except Exception as e:
        # 超限或其他异常时，尝试从已有消息中提取最后一条文本回答
        if "usage_limit" in str(e).lower() or "request_limit" in str(e).lower():
            logger.warning(f"请求次数超限，尝试提取已有结果 | session_id={session_id}")
            # 从 run 的消息历史中提取最后的文本内容
            last_text = _extract_last_text(run) if 'run' in dir() else ""
            if last_text:
                from types import SimpleNamespace
                result = SimpleNamespace(output=last_text)
            else:
                raise
        else:
            raise

    logger.info(
        f"结果提取 | session_id={session_id} "
        f"output_type={type(result.output).__name__} "
        f"output_preview={str(result.output)[:300]}"
    )

    return result


async def _run_orchestration(
    session_id: str,
    trace_id: str,
    request: QueryRequest,
) -> None:
    """异步执行编排流程（支持 DIRECT → AUTO 模式升级）"""
    session_id_var.set(session_id)
    trace_id_var.set(trace_id)

    try:
        # 推送会话创建事件
        await _publish(session_id, {"event_type": "session_created", "session_id": session_id})

        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.PLANNING)

        # Stage 1: Reason
        plan = await _reasoning_engine.decide(request.query, request.mode)

        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.EXECUTING)

        # Stage 2: Execute
        result = await _execute_plan(plan, request, session_id, trace_id)

        # Stage 2.5: 模式升级检查（仅 DIRECT → AUTO，最多一次）
        if _needs_escalation(result, plan):
            escalated = escalate_plan(plan, ExecutionMode.AUTO)
            logger.info(
                f"模式升级 | session_id={session_id} "
                f"{plan.mode.value} → {escalated.mode.value}"
            )
            await _publish(session_id, {
                "event_type": "mode_escalated",
                "from_mode": plan.mode.value,
                "to_mode": escalated.mode.value,
            })
            result = await _execute_plan(escalated, request, session_id, trace_id)
            plan = escalated

        # 推送完成事件
        output = result.output if hasattr(result, "output") else str(result)
        answer = output if isinstance(output, str) else output.answer if hasattr(output, "answer") else str(output)
        logger.info(
            f"结果提取 | session_id={session_id} "
            f"output_type={type(output).__name__} "
            f"answer_len={len(answer)}"
        )
        await _publish(session_id, {
            "event_type": "session_completed",
            "answer": answer,
        })

        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.COMPLETED)

        logger.info(f"编排完成 | session_id={session_id} mode={plan.mode.value}")

    except Exception as e:
        logger.error(f"编排失败 | session_id={session_id} error={e}")
        await _publish(session_id, {"event_type": "session_failed", "error": str(e)})
        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.FAILED)


async def _publish(session_id: str, event: dict[str, Any]) -> None:
    """发布事件到 Redis Stream"""
    if _stream_adapter:
        await _stream_adapter.publish(session_id, event)
