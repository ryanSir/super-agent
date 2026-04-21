"""Base Tools — 内置工具（按职责分组）

将 Workers、Skills、Memory 等底层服务包装为 Agent 可调用的工具函数。
主 Agent 和 Sub-Agent 共享同一批工具实例。
返回按职责分组的 dict，为后续 Toolset 化重构铺路。

事件发布和 Langfuse tracing 由 EventPublishingCapability 统一处理。
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from pydantic_ai import RunContext

from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import RiskLevel, TaskNode, TaskType
from src_deepagent.capabilities.skills.registry import skill_registry

logger = get_logger(__name__)


def create_base_tools(workers: dict[str, Any]) -> dict[str, list[Callable]]:
    """将 Worker 实例包装为按职责分组的工具函数字典

    Args:
        workers: Worker 名称到实例的映射

    Returns:
        按职责分组的工具函数字典（native/sandbox/ui/memory/plan/skill_mgmt）
    """

    async def execute_sandbox(
        ctx: RunContext[Any],
        instruction: str,
        context_files: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """调用 SandboxWorker 在隔离环境中执行自定义代码片段

        ⚠️ 注意：此工具用于执行临时的自定义代码。
        如需调用已注册的 Skill，必须使用 execute_skill，不要用此工具替代——
        Skill 需要注入专属文件，直接用此工具会因缺少文件而失败。

        Args:
            instruction: 执行指令
            context_files: 注入沙箱的文件（路径→内容）
            timeout: 超时秒数
        """
        worker = workers.get("sandbox_worker")
        if not worker:
            return {"success": False, "error": "SandboxWorker 不可用"}

        task = TaskNode(
            task_id=f"sb-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.SANDBOX_CODING,
            risk_level=RiskLevel.DANGEROUS,
            input_data={
                "instruction": instruction,
                "context_files": context_files or {},
                "timeout": timeout,
            },
        )
        result = await worker.execute(task)
        return result.model_dump()

    async def execute_skill(
        ctx: RunContext[Any],
        skill_name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行已注册的 Skill（仅限 sandbox 模式）

        仅用于 execution: sandbox 的 Skill。Native 模式的 Skill 请使用
        load_skill 加载后直接用 Base Tool 执行。

        Args:
            skill_name: 技能名称（从 list_skills 结果中获取）
            params: 技能参数
        """
        skill = skill_registry.get(skill_name)
        if not skill:
            return {"success": False, "error": f"技能 '{skill_name}' 未找到"}

        # 模式检查：native skill 不走沙箱
        if skill.metadata.execution == "native":
            return {
                "success": False,
                "error": (
                    f"技能 '{skill_name}' 为 native 模式，请使用 load_skill 加载后直接执行"
                ),
            }

        # Skill 通过沙箱执行
        sandbox_worker = workers.get("sandbox_worker")
        if not sandbox_worker:
            return {"success": False, "error": "SandboxWorker 不可用，无法执行 Skill"}

        # 读取 skill 目录下的所有文件，注入沙箱
        import os
        from pathlib import Path

        context_files: dict[str, str] = {}
        skill_path = Path(skill.metadata.path)

        # 注入脚本文件
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for f in scripts_dir.iterdir():
                if f.is_file():
                    try:
                        context_files[f"scripts/{f.name}"] = f.read_text(encoding="utf-8")
                    except Exception:
                        pass

        # 注入参考文档
        refs_dir = skill_path / "references"
        if refs_dir.exists():
            for f in refs_dir.iterdir():
                if f.is_file():
                    try:
                        context_files[f"references/{f.name}"] = f.read_text(encoding="utf-8")
                    except Exception:
                        pass

        # 注入 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                context_files["SKILL.md"] = skill_md.read_text(encoding="utf-8")
            except Exception:
                pass

        # 构建执行指令
        scripts = skill.scripts
        main_script = scripts[0] if scripts else "main.py"
        params_json = json.dumps(params or {}, ensure_ascii=False)

        # 构建执行指令：让 Pi Agent 根据 SKILL.md 理解参数并正确执行
        instruction = (
            f"请执行技能 '{skill_name}'。\n"
            f"主脚本: scripts/{main_script}\n"
            f"技能描述: {skill.metadata.description}\n"
            f"用户传入参数: {params_json}\n\n"
            f"重要：所有文件已注入当前工作目录。\n"
            f"- SKILL.md 在 ./SKILL.md\n"
            f"- 脚本在 ./scripts/ 目录下\n"
            f"请先阅读 ./SKILL.md 了解脚本的正确用法和参数格式，"
            f"然后根据文档说明构建正确的命令行来执行脚本。"
            f"不要直接把 JSON 作为参数传给脚本。\n"
            f"如果脚本需要依赖，先用 pip install 安装。"
        )

        task = TaskNode(
            task_id=f"skill-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.SANDBOX_CODING,
            risk_level=RiskLevel.DANGEROUS,
            description=f"执行技能: {skill_name}",
            input_data={
                "instruction": instruction,
                "context_files": context_files,
                "timeout": (params or {}).get("timeout", 300),
            },
        )

        logger.info(
            f"执行 Skill | name={skill_name} script={main_script} "
            f"context_files={len(context_files)} params={params_json[:100]}"
        )
        result = await sandbox_worker.execute(task)
        return result.model_dump()

    async def emit_chart(
        ctx: RunContext[Any],
        title: str,
        chart_type: str,
        x_axis: list[str] | None = None,
        series_data: Any = None,
    ) -> dict[str, Any]:
        """渲染 ECharts 图表到前端

        Args:
            title: 图表标题
            chart_type: 图表类型（bar/line/pie/scatter）
            x_axis: X 轴数据
            series_data: 系列数据
        """
        widget_id = f"chart-{uuid.uuid4().hex[:8]}"
        props = {
            "title": title,
            "chartType": chart_type,
            "xAxis": x_axis or [],
            "seriesData": series_data or [],
        }

        logger.info(f"图表渲染 | title={title} type={chart_type} widget_id={widget_id}")

        # render_widget 事件由 EventPublishingCapability.after_tool_execute 推送

        return {
            "success": True,
            "data": {
                "widget_id": widget_id,
                "ui_component": "DataChart",
                "props": props,
            },
        }

    async def plan_and_decompose(
        ctx: RunContext[Any],
        query: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """调用 Planner Agent 生成 ExecutionDAG

        使用轻量 LLM 将用户查询分解为结构化的子任务 DAG。

        Args:
            query: 用户查询
            context: 附加上下文
        """
        from src_deepagent.llm.registry import get_model_for_role
        from src_deepagent.orchestrator.planning import PLANNING_PROMPT

        logger.info(f"任务规划 | query={query[:80]}")

        try:
            from pydantic_ai import Agent

            planner = Agent(
                model=get_model_for_role("planner"),
                output_type=list[dict[str, Any]],
                instructions=PLANNING_PROMPT,
                name="Planner",
                retries=2,
            )

            result = await planner.run(
                f"请为以下用户请求生成任务 DAG：\n\n{query}"
                + (f"\n\n附加上下文：{json.dumps(context, ensure_ascii=False)}" if context else "")
            )

            tasks = result.output if hasattr(result, "output") else result.data
            dag_id = f"dag-{uuid.uuid4().hex[:8]}"

            return {
                "success": True,
                "data": {
                    "dag_id": dag_id,
                    "query": query,
                    "tasks": tasks if isinstance(tasks, list) else [],
                },
            }
        except Exception as e:
            logger.error(f"任务规划失败 | error={e}")
            return {
                "success": False,
                "error": f"任务规划失败: {e}",
                "data": {"dag_id": "", "query": query, "tasks": []},
            }

    async def baidu_search(
        ctx: RunContext[Any],
        query: str,
        count: int = 10,
        freshness: str | None = None,
    ) -> dict[str, Any]:
        """网络搜索 — 通过百度 AI 搜索引擎检索网页信息

        Args:
            query: 搜索关键词
            count: 返回结果数量（1-50，默认10）
            freshness: 时间过滤，可选值：
                - "pd" 过去24小时
                - "pw" 过去7天
                - "pm" 过去31天
                - "py" 过去一年
                - "2024-01-01to2024-06-01" 自定义范围
        """
        worker = workers.get("web_search_worker")
        if not worker:
            return {"success": False, "error": "WebSearchWorker 不可用"}

        logger.info(f"百度搜索 | query={query} count={count} freshness={freshness}")
        task = TaskNode(
            task_id=f"search-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.WEB_SEARCH,
            input_data={"query": query, "count": count, "freshness": freshness},
        )
        result = await worker.execute(task)
        return result.model_dump() if hasattr(result, "model_dump") else result

    async def create_skill(
        ctx: RunContext[Any],
        name: str,
        description: str,
        script_name: str = "main.py",
        script_content: str | None = None,
        doc_content: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """创建新技能包，生成 SKILL.md 和脚本模板并注册到技能库。

        可先调用 search_skills 确认无同名技能，再调用此工具创建。
        如果技能已存在且需要覆盖，传 overwrite=True。

        Args:
            name: 技能名称（小写字母 + 连字符，如 my-skill）
            description: 技能一句话描述
            script_name: 主脚本文件名（默认 main.py）
            script_content: 脚本内容（可选，不提供则生成模板）
            doc_content: 附加文档内容（追加到 SKILL.md，可选）
            overwrite: 是否覆盖已存在的技能目录（默认 False）
        """
        from src_deepagent.capabilities.skill_creator import (
            SkillCreateRequest,
            create_skill as _create_skill,
        )

        request = SkillCreateRequest(
            name=name,
            description=description,
            script_name=script_name,
            script_content=script_content,
            doc_content=doc_content,
            overwrite=overwrite,
        )
        return _create_skill(request)

    # 按职责分组，为后续 Toolset 化重构铺路
    return {
        "native": [baidu_search],
        "sandbox": [execute_sandbox, execute_skill],
        "ui": [emit_chart],
        "memory": [],
        "plan": [plan_and_decompose],
        "skill_mgmt": [create_skill],
    }
