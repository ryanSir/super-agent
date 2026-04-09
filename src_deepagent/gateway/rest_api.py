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
from src_deepagent.orchestrator.reasoning_engine import ReasoningEngine
from src_deepagent.schemas.agent import OrchestratorOutput, SessionStatus
from src_deepagent.schemas.api import QueryRequest, QueryResponse
from src_deepagent.state.session_manager import SessionManager
from src_deepagent.streaming.sse_endpoint import sse_event_generator
from src_deepagent.streaming.stream_adapter import StreamAdapter
from src_deepagent.sub_agents.factory import create_sub_agent_configs

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# ── Worker 注册表 ────────────────────────────────────────

_WORKER_REGISTRY: dict[str, tuple[str, str]] = {
    "sandbox_worker": ("src_deepagent.workers.sandbox.sandbox_worker", "SandboxWorker"),
    "rag_worker": ("src_deepagent.workers.native.rag_worker", "RAGWorker"),
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


async def _run_orchestration(
    session_id: str,
    trace_id: str,
    request: QueryRequest,
) -> None:
    """异步执行编排流程"""
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
        sub_agent_configs = create_sub_agent_configs(plan.resources.bridge_tools)
        agent, deps = create_orchestrator_agent(
            plan=plan,
            sub_agent_configs=sub_agent_configs,
            session_id=session_id,
            trace_id=trace_id,
            publish_fn=_publish,
        )

        # 构建 effective query
        effective_query = plan.prompt_prefix + request.query

        # 执行 Agent
        result = await agent.run(effective_query, deps=deps)

        # 推送完成事件
        output = result.output if hasattr(result, "output") else str(result)
        await _publish(session_id, {
            "event_type": "session_completed",
            "answer": output if isinstance(output, str) else output.answer if hasattr(output, "answer") else str(output),
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
