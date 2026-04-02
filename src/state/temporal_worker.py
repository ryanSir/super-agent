"""Temporal Worker 注册

连接本地 Temporal 服务，注册 Workflow 和 Activity。
"""

# 标准库
import asyncio
from datetime import timedelta
from typing import Any, Dict, Optional

# 第三方库
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger
from src.state.activities import (
    collect_results,
    execute_native_worker,
    execute_sandbox_worker,
    plan_task,
)
from src.state.workflows import AgentWorkflow

logger = get_logger(__name__)

_temporal_client: Optional[Client] = None


# ============================================================
# OrchestratorWorkflow：薄包装，委托给现有 PydanticAI 编排逻辑
# ============================================================

@activity.defn
async def run_orchestration(params: Dict[str, Any]) -> None:
    """执行完整编排流程的 Activity

    直接调用现有 _run_orchestration()，通过 Redis Streams 推送事件。

    Args:
        params: {session_id, trace_id, query, context, mode}
    """
    from src.gateway.rest_api import _run_orchestration
    from src.schemas.api import QueryRequest

    session_id = params["session_id"]
    trace_id = params.get("trace_id", "")
    request = QueryRequest(
        query=params["query"],
        session_id=session_id,
        context=params.get("context", {}),
        mode=params.get("mode", "auto"),
    )

    logger.info(f"[Activity:run_orchestration] 开始编排 | session_id={session_id}")
    await _run_orchestration(session_id, trace_id, request)
    logger.info(f"[Activity:run_orchestration] 编排完成 | session_id={session_id}")


@workflow.defn
class OrchestratorWorkflow:
    """编排工作流（薄包装）

    将完整编排逻辑委托给 run_orchestration activity，
    获得 Temporal 的持久化、崩溃恢复和任务去重能力。
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> None:
        await workflow.execute_activity(
            run_orchestration,
            params,
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


async def get_temporal_client() -> Client:
    """获取 Temporal 客户端单例"""
    global _temporal_client
    if _temporal_client is None:
        settings = get_settings()
        _temporal_client = await Client.connect(settings.temporal.temporal_host)
        logger.info(
            f"[Temporal] 连接成功 | host={settings.temporal.temporal_host}"
        )
    return _temporal_client


async def start_temporal_worker() -> Worker:
    """启动 Temporal Worker

    注册 OrchestratorWorkflow、AgentWorkflow 和所有 Activity。

    Returns:
        运行中的 Worker 实例
    """
    settings = get_settings()
    client = await get_temporal_client()

    worker = Worker(
        client,
        task_queue=settings.temporal.temporal_task_queue,
        workflows=[OrchestratorWorkflow, AgentWorkflow],
        activities=[
            run_orchestration,
            plan_task,
            execute_native_worker,
            execute_sandbox_worker,
            collect_results,
        ],
    )

    logger.info(
        f"[Temporal] Worker 启动 | "
        f"task_queue={settings.temporal.temporal_task_queue} "
        f"workflows=[OrchestratorWorkflow, AgentWorkflow] activities=5"
    )
    return worker


async def submit_orchestrator_workflow(
    query: str,
    session_id: str,
    trace_id: str = "",
    context: Optional[dict] = None,
    mode: str = "auto",
) -> str:
    """提交 OrchestratorWorkflow 到 Temporal

    Args:
        query: 用户请求
        session_id: 会话 ID
        trace_id: 追踪 ID
        context: 附加上下文
        mode: 执行模式

    Returns:
        Workflow Run ID
    """
    settings = get_settings()
    client = await get_temporal_client()

    handle = await client.start_workflow(
        OrchestratorWorkflow.run,
        {
            "query": query,
            "session_id": session_id,
            "trace_id": trace_id,
            "context": context or {},
            "mode": mode,
        },
        id=f"agent-{session_id}",
        task_queue=settings.temporal.temporal_task_queue,
    )

    logger.info(
        f"[Temporal] OrchestratorWorkflow 已提交 | "
        f"workflow_id=agent-{session_id} run_id={handle.result_run_id}"
    )
    return handle.result_run_id


async def submit_workflow(
    query: str,
    session_id: str,
    trace_id: str = "",
    context: Optional[dict] = None,
) -> str:
    """提交 AgentWorkflow 到 Temporal

    Args:
        query: 用户请求
        session_id: 会话 ID
        trace_id: 追踪 ID
        context: 附加上下文

    Returns:
        Workflow Run ID
    """
    settings = get_settings()
    client = await get_temporal_client()

    handle = await client.start_workflow(
        AgentWorkflow.run,
        {
            "query": query,
            "session_id": session_id,
            "trace_id": trace_id,
            "context": context or {},
        },
        id=f"agent-{session_id}",
        task_queue=settings.temporal.temporal_task_queue,
    )

    logger.info(
        f"[Temporal] Workflow 已提交 | "
        f"workflow_id=agent-{session_id} run_id={handle.result_run_id}"
    )
    return handle.result_run_id
