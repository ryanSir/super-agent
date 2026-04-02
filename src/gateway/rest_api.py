"""REST API 端点

提供查询提交、SSE 流式响应等 HTTP 接口。
"""

# 标准库
import uuid
from typing import Optional

# 第三方库
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette.requests import Request

# 本地模块
from src.config.settings import Settings, get_settings
from src.core.logging import get_logger, session_id_var
from src.monitoring.pipeline_events import pipeline_step
from src.monitoring.trace_context import set_trace_context
from src.orchestrator.orchestrator_agent import run_orchestrator
from src.schemas.api import QueryRequest, QueryResponse
from src.streaming.stream_adapter import publish_event

logger = get_logger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def submit_query(
        request: QueryRequest,
        settings: Settings = Depends(get_settings),
) -> QueryResponse:
    """提交查询请求

    接收用户自然语言请求，启动 Orchestrator 编排流程。
    返回 session_id 和 trace_id，客户端可通过 SSE/WebSocket 获取实时进度。

    Args:
        request: 查询请求体
        settings: 应用配置

    Returns:
        QueryResponse: 包含 session_id 和 trace_id
    """
    session_id = request.session_id or f"sess-{uuid.uuid4().hex[:12]}"
    trace_id = set_trace_context(session_id=session_id)
    session_id_var.set(session_id)
    logger.info(
        f"[Gateway] 收到查询请求 | "
        f"session_id={session_id} trace_id={trace_id} "
        f"query_len={len(request.query)} mode={request.mode}"
    )

    # 优先通过 Temporal 提交工作流，失败时降级为直接执行
    import asyncio
    try:
        from src.state.temporal_worker import submit_orchestrator_workflow
        run_id = await submit_orchestrator_workflow(
            query=request.query,
            session_id=session_id,
            trace_id=trace_id,
            context=request.context,
            mode=request.mode,
        )
        asyncio.create_task(publish_event(session_id, {
            "event_type": "workflow_submitted",
            "workflow_id": f"agent-{session_id}",
            "run_id": run_id,
        }))
    except Exception as e:
        logger.warning(f"[Gateway] Temporal 不可用，降级为直接执行 | error={e}")
        asyncio.create_task(publish_event(session_id, {
            "event_type": "workflow_fallback",
            "detail": str(e),
        }))
        asyncio.create_task(_run_orchestration(session_id, trace_id, request))

    return QueryResponse(
        success=True,
        session_id=session_id,
        trace_id=trace_id,
        message="查询已提交，请通过 SSE 或 WebSocket 获取实时进度",
    )


@router.get("/stream/{session_id}")
async def stream_events(
        session_id: str,
        request: Request,
):
    """SSE 流式事件推送，支持 Last-Event-ID 断点续传

    客户端通过此端点订阅指定会话的实时事件流。
    浏览器 EventSource 断线重连时自动发送 Last-Event-ID 请求头。

    Args:
        session_id: 会话 ID
        request: HTTP 请求（用于读取 Last-Event-ID）

    Returns:
        SSE EventSource 流
    """
    from src.streaming.sse_endpoint import create_sse_response

    last_event_id = request.headers.get("Last-Event-ID", "0-0")

    logger.info(
        f"[Gateway] SSE 连接建立 | session_id={session_id} last_event_id={last_event_id}"
    )

    return create_sse_response(session_id, last_event_id=last_event_id)


@router.get("/health")
async def gateway_health():
    """网关健康检查"""
    return {"status": "ok", "service": "agent-gateway"}


# ============================================================
# Metrics 端点
# ============================================================

@router.get("/metrics/overview")
async def metrics_overview(window: int = 5):
    """各步骤耗时统计概览

    Args:
        window: 统计时间窗口（分钟），默认 5 分钟
    """
    from src.monitoring.execution_metrics import get_metrics_collector
    collector = get_metrics_collector()
    stats = collector.get_overview(window_minutes=window)
    return {
        "window_minutes": window,
        "steps": [
            {
                "count": s.count,
                "avg_ms": round(s.avg_ms, 1),
                "p50_ms": round(s.p50_ms, 1),
                "p95_ms": round(s.p95_ms, 1),
                "p99_ms": round(s.p99_ms, 1),
                "max_ms": round(s.max_ms, 1),
                "error_count": s.error_count,
                "error_rate": round(s.error_rate, 3),
            }
            for s in stats
        ],
    }


@router.get("/metrics/step/{step_name:path}")
async def metrics_step(step_name: str, window: int = 5):
    """查询指定步骤的耗时统计

    Args:
        step_name: 步骤名称（如 gateway.receive, worker.sandbox.execute）
        window: 统计时间窗口（分钟）
    """
    from src.monitoring.execution_metrics import get_metrics_collector
    collector = get_metrics_collector()
    s = collector.get_step_stats(step_name, window_minutes=window)
    return {
        "step": step_name,
        "window_minutes": window,
        **{
            "count": s.count,
            "avg_ms": round(s.avg_ms, 1),
            "p50_ms": round(s.p50_ms, 1),
            "p95_ms": round(s.p95_ms, 1),
            "p99_ms": round(s.p99_ms, 1),
            "max_ms": round(s.max_ms, 1),
            "error_count": s.error_count,
            "error_rate": round(s.error_rate, 3),
        },
    }


@router.get("/metrics/trace/{trace_id}")
async def metrics_trace(trace_id: str):
    """查询指定 trace 的完整链路时间线"""
    from src.monitoring.execution_metrics import get_metrics_collector
    collector = get_metrics_collector()
    events = collector.get_trace_timeline(trace_id)
    return {
        "trace_id": trace_id,
        "events": [
            {
                "step": ev.step,
                "status": ev.status.value,
                "duration_ms": round(ev.duration_ms, 1) if ev.duration_ms else None,
                "metadata": ev.metadata,
                "timestamp": ev.timestamp,
            }
            for ev in events
        ],
    }


# ============================================================
# Skill 管理端点
# ============================================================

@router.get("/skills")
async def list_skills():
    """列出所有已注册的 Skill"""
    from src.skills.registry import skill_registry

    skills = skill_registry.list_skills()
    return {
        "success": True,
        "skills": [
            {
                "name": s.metadata.name,
                "description": s.metadata.description,
                "scripts": s.scripts,
                "references": s.references,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str):
    """获取 Skill 详情（含 SKILL.md 内容）"""
    from src.skills.registry import skill_registry

    info = skill_registry.get(skill_name)
    if not info:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f"Skill '{skill_name}' 不存在"},
        )

    return {
        "success": True,
        "skill": {
            "name": info.metadata.name,
            "description": info.metadata.description,
            "scripts": info.scripts,
            "references": info.references,
            "doc_content": info.doc_content,
        },
    }


@router.post("/skills")
async def create_skill(request: dict):
    """创建新 Skill"""
    from src.skills.creator import create_skill as do_create
    from src.skills.schema import SkillCreateRequest

    try:
        req = SkillCreateRequest(**request)
        info = await do_create(req)
        return {
            "success": True,
            "skill": {
                "name": info.metadata.name,
                "description": info.metadata.description,
                "scripts": info.scripts,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)},
        )


@router.post("/skills/{skill_name}/execute")
async def execute_skill(skill_name: str, request: dict = None):
    """执行 Skill"""
    from src.skills.executor import execute_skill as run_skill
    from src.skills.schema import SkillExecuteRequest

    req = SkillExecuteRequest(
        skill_name=skill_name,
        args=request.get("args", []) if request else [],
        env=request.get("env", {}) if request else {},
        timeout=request.get("timeout", 60) if request else 60,
    )
    result = await run_skill(req)
    return {
        "success": result.success,
        "result": result.model_dump(),
    }


# ============================================================
# 内部函数
# ============================================================

# Worker 注册表：name → (module_path, class_name)
_WORKER_REGISTRY = {
    "sandbox_worker": ("src.workers.sandbox.sandbox_worker", "SandboxWorker"),
    "rag_worker": ("src.workers.native.rag_worker", "RAGWorker"),
    "db_query_worker": ("src.workers.native.db_query_worker", "DBQueryWorker"),
    "api_call_worker": ("src.workers.native.api_call_worker", "APICallWorker"),
}


def _init_workers() -> dict:
    """按需加载 Worker 实例，缺依赖时跳过"""
    import importlib
    workers = {}
    for name, (module_path, class_name) in _WORKER_REGISTRY.items():
        try:
            module = importlib.import_module(module_path)
            workers[name] = getattr(module, class_name)()
        except Exception as e:
            logger.warning(f"[Gateway] {class_name} 初始化失败 | error={e}")
    return workers


async def _run_orchestration(
        session_id: str,
        trace_id: str,
        request: QueryRequest,
) -> None:
    """异步执行编排流程，事件持久化到 Redis Stream

    职责：session 生命周期管理 + answer 流式输出。
    step / tool_result 事件由 orchestrator 内部的 tool 直接推送。
    """
    workers = _init_workers()

    # 会话开始
    await publish_event(session_id, {
        "event_type": "session_created",
        "session_id": session_id,
        "trace_id": trace_id,
    })
    await publish_event(session_id, {
        "event_type": "thinking",
        "content": "正在分析您的请求...\n",
    })

    accumulated_answer = []
    try:
        async with pipeline_step("gateway.respond", session_id=session_id):
            answer_step_started = False

            async for token in run_orchestrator(
                    query=request.query,
                    session_id=session_id,
                    workers=workers,
                    context=request.context,
                    mode=request.mode,
            ):
                if not token:
                    continue

                # 第一个 token 到来时推送 answer step（确保在 orchestrator 内部事件之后）
                if not answer_step_started:
                    answer_step_started = True
                    await publish_event(session_id, {
                        "event_type": "step",
                        "step_id": "answer",
                        "title": "整合分析结果",
                        "status": "running",
                    })

                accumulated_answer.append(token)
                await publish_event(session_id, {
                    "event_type": "text_stream",
                    "delta": token,
                    "is_final": False,
                })

            # 流式结束标记
            await publish_event(session_id, {
                "event_type": "text_stream",
                "delta": "",
                "is_final": True,
            })
            if answer_step_started:
                await publish_event(session_id, {
                    "event_type": "step",
                    "step_id": "answer",
                    "title": "整合分析结果",
                    "status": "completed",
                })

            # 会话完成
            await publish_event(session_id, {
                "event_type": "session_completed",
                "session_id": session_id,
                "trace_id": trace_id,
            })
            logger.info(f"[Gateway] 编排完成 | session_id={session_id} trace_id={trace_id}")

    except Exception as e:
        logger.error(f"[Gateway] 编排失败 | session_id={session_id} error={e}", exc_info=True)
        await publish_event(session_id, {
            "event_type": "session_failed",
            "session_id": session_id,
            "trace_id": trace_id,
            "error": str(e),
            "partial_answer_len": len("".join(accumulated_answer)),
        })
