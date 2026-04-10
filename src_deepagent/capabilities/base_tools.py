"""Base Tools — 10 个内置工具

将 Workers、Skills、Memory 等底层服务包装为 Agent 可调用的工具函数。
主 Agent 和 Sub-Agent 共享同一批工具实例。
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from pydantic_ai import RunContext

from src_deepagent.core.exceptions import BridgeError
from src_deepagent.core.logging import get_logger
from src_deepagent.memory.retriever import MemoryRetriever
from src_deepagent.schemas.agent import RiskLevel, TaskNode, TaskStatus, TaskType
from src_deepagent.capabilities.skills.registry import skill_registry

logger = get_logger(__name__)


def create_base_tools(workers: dict[str, Any]) -> list[Callable]:
    """将 Worker 实例包装为工具函数列表

    Args:
        workers: Worker 名称到实例的映射

    Returns:
        Agent 可调用的工具函数列表
    """

    async def execute_rag_search(ctx: RunContext[Any], query: str, top_k: int = 5) -> dict[str, Any]:
        """调用 RAGWorker 进行向量检索

        Args:
            query: 检索查询文本
            top_k: 返回结果数量
        """
        worker = workers.get("rag_worker")
        if not worker:
            return {"success": False, "error": "RAGWorker 不可用"}

        task = TaskNode(
            task_id=f"rag-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.RAG_RETRIEVAL,
            input_data={"query": query, "top_k": top_k},
        )
        result = await worker.execute(task)
        return result.model_dump()

    async def execute_db_query(ctx: RunContext[Any], sql: str) -> dict[str, Any]:
        """调用 DBQueryWorker 执行只读 SQL 查询

        Args:
            sql: SQL 查询语句（仅支持 SELECT）
        """
        worker = workers.get("db_query_worker")
        if not worker:
            return {"success": False, "error": "DBQueryWorker 不可用"}

        task = TaskNode(
            task_id=f"db-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.DB_QUERY,
            input_data={"sql": sql},
        )
        result = await worker.execute(task)
        return result.model_dump()

    async def execute_api_call(
        ctx: RunContext[Any],
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """调用 APICallWorker 发起 HTTP 请求

        Args:
            url: 请求 URL
            method: HTTP 方法（GET/POST/PUT/DELETE）
            headers: 请求头
            body: 请求体（JSON）
            params: URL 查询参数
        """
        worker = workers.get("api_call_worker")
        if not worker:
            return {"success": False, "error": "APICallWorker 不可用"}

        task = TaskNode(
            task_id=f"api-{uuid.uuid4().hex[:8]}",
            task_type=TaskType.API_CALL,
            input_data={
                "url": url,
                "method": method,
                "headers": headers or {},
                "body": body,
                "params": params,
            },
        )
        result = await worker.execute(task)
        return result.model_dump()

    async def execute_sandbox(
        ctx: RunContext[Any],
        instruction: str,
        context_files: dict[str, str] | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """调用 SandboxWorker 在 E2B 隔离环境中执行任务

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
        """执行已注册的 Skill

        Args:
            skill_name: 技能名称
            params: 技能参数
        """
        skill = skill_registry.get(skill_name)
        if not skill:
            return {"success": False, "error": f"技能 '{skill_name}' 未找到"}

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

        # 构建 instruction：让 Pi Agent 理解任务并执行脚本
        instruction = (
            f"请执行技能 '{skill_name}'。\n"
            f"运行命令: python3 scripts/{main_script} '{params_json}'\n"
            f"技能描述: {skill.metadata.description}\n"
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
                "timeout": 120,
            },
        )

        logger.info(
            f"执行 Skill | name={skill_name} script={main_script} "
            f"context_files={len(context_files)} params={params_json[:100]}"
        )
        result = await sandbox_worker.execute(task)
        return result.model_dump()

    async def search_skills(ctx: RunContext[Any], query: str) -> dict[str, Any]:
        """搜索可用 Skills

        Args:
            query: 搜索关键词
        """
        from src_deepagent.capabilities.skills.registry import skill_registry

        results = skill_registry.search_skills(query)
        return {
            "success": True,
            "data": [
                {
                    "name": s.metadata.name,
                    "description": s.metadata.description,
                    "scripts": s.scripts,
                    "doc_content": s.doc_content[:2000],
                }
                for s in results
            ],
            "count": len(results),
        }

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
        chart_config = {
            "title": {"text": title},
            "xAxis": {"data": x_axis or []},
            "series": series_data or [],
            "chart_type": chart_type,
        }

        # 通过 A2UI 协议推送到前端
        frame = {
            "component": "DataChart",
            "props": {"option": chart_config, "style": {"height": "400px"}},
        }

        logger.info(f"图表渲染 | title={title} type={chart_type}")
        return {"success": True, "data": frame}

    async def recall_memory(ctx: RunContext[Any], user_id: str) -> dict[str, Any]:
        """从 Redis 检索用户记忆

        Args:
            user_id: 用户 ID
        """
        try:
            retriever = MemoryRetriever()
            memory_text = await retriever.retrieve(user_id)
            return {"success": True, "data": {"memory": memory_text}}
        except Exception as e:
            logger.warning(f"记忆检索失败 | user_id={user_id} error={e}")
            return {"success": True, "data": {"memory": ""}}

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
        from src_deepagent.llm.config import get_model
        from src_deepagent.orchestrator.planning import PLANNING_PROMPT

        logger.info(f"任务规划 | query={query[:80]}")

        try:
            from pydantic_ai import Agent

            planner = Agent(
                model=get_model("planning"),
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

    async def tool_search(ctx: RunContext[Any], query: str) -> dict[str, Any]:
        """搜索并加载外部工具（MCP 渐进式加载）

        支持三种搜索模式：
        - "select:name1,name2" → 精确匹配指定工具
        - "+keyword" → 名称包含关键词
        - "keyword" → 正则匹配名称和描述

        Args:
            query: 搜索查询
        """
        from src_deepagent.capabilities.mcp.deferred_registry import deferred_tool_registry

        results = deferred_tool_registry.search(query)
        if not results:
            return {
                "success": True,
                "data": {"tools": [], "count": 0},
                "message": f"未找到匹配 '{query}' 的工具",
            }

        tools_data = [
            {
                "name": t.name,
                "description": t.description,
                "schema": t.schema,
                "server": t.server_name,
            }
            for t in results
        ]

        logger.info(f"工具搜索 | query={query} found={len(results)}")
        return {
            "success": True,
            "data": {"tools": tools_data, "count": len(results)},
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
        import os
        from src_deepagent.workers.native.web_search_worker import web_search as _search

        logger.info(f"百度搜索 | query={query} count={count} freshness={freshness}")
        api_key = os.getenv("BAIDU_API_KEY", "")
        return await _search(api_key, query, count, freshness)

    return [
        execute_rag_search,
        execute_db_query,
        execute_api_call,
        execute_sandbox,
        execute_skill,
        search_skills,
        emit_chart,
        recall_memory,
        plan_and_decompose,
        tool_search,
        baidu_search,
    ]
