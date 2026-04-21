"""REST API 网关

POST /api/agent/query — 提交查询
GET /api/agent/stream/{session_id} — SSE 事件流
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import AsyncIterable
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta, ThinkingPartDelta

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger, session_id_var, trace_id_var
from src_deepagent.llm.catalog import reload_catalog
from src_deepagent.llm.registry import get_model_bundle
from src_deepagent.orchestrator.agent_factory import create_orchestrator_agent
from src_deepagent.orchestrator.reasoning_engine import ReasoningEngine
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
    "web_search_worker": ("src_deepagent.workers.native.web_search_worker", "WebSearchWorker"),
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


async def startup() -> None:
    """启动预热：MCP 连接 + 定期刷新任务（由 main.py lifespan 调用）"""
    if _reasoning_engine:
        await _reasoning_engine.startup()


async def shutdown() -> None:
    """关闭清理：停止刷新任务（由 main.py lifespan 调用）"""
    if _reasoning_engine:
        await _reasoning_engine.shutdown()


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


@router.get("/skills")
async def list_skills():
    """返回已注册的 Skill 列表"""
    from src_deepagent.capabilities.skills.registry import skill_registry

    skills = [
        {
            "name": info.metadata.name,
            "description": info.metadata.description,
        }
        for info in skill_registry._skills.values()
    ]
    return {"skills": skills}


@router.post("/skills", status_code=201)
async def create_skill_endpoint(request: dict):
    """创建新技能包

    Body 字段：
    - name: 技能名称（小写字母 + 连字符）
    - description: 技能描述
    - script_name: 主脚本文件名（默认 main.py）
    - script_content: 脚本内容（可选）
    - doc_content: 附加文档（可选）
    - overwrite: 是否覆盖（默认 false）
    """
    from fastapi import HTTPException
    from pydantic import ValidationError
    from src_deepagent.capabilities.skill_creator import SkillCreateRequest, create_skill

    try:
        req = SkillCreateRequest(**request)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    result = create_skill(req)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result["data"]


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


@router.post("/admin/reload-mcp")
async def reload_mcp() -> dict:
    """手动触发 MCP 工具刷新（运维接口）"""
    if not _reasoning_engine:
        raise HTTPException(status_code=503, detail="服务未初始化")
    tool_count = await _reasoning_engine.reload_mcp()
    return {"success": True, "tool_count": tool_count}


@router.post("/admin/reload-models")
async def reload_models() -> dict:
    """手动触发模型目录重载（运维接口）"""
    catalog = reload_catalog()
    return {
        "success": True,
        "providers": list(catalog.providers.keys()),
        "models": list(catalog.models.keys()),
        "roles": catalog.roles,
    }


# ── 编排执行 ─────────────────────────────────────────────


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


def _extract_last_text_from_result(result: Any) -> str:
    """从 agent result 中提取文本回答（兜底）"""
    try:
        if hasattr(result, "all_messages"):
            for msg in reversed(result.all_messages()):
                if hasattr(msg, "parts"):
                    for part in reversed(msg.parts):
                        if hasattr(part, "content") and isinstance(part.content, str) and part.content.strip():
                            return part.content.strip()
    except Exception:
        pass
    return str(result.output)[:2000] if hasattr(result, "output") else ""


async def _run_agent(
    decision: Any,
    request: QueryRequest,
    session_id: str,
    trace_id: str,
    message_history: list[Any] | None = None,
) -> Any:
    """根据推理决策创建并运行 Agent，流式推送 A2UI 事件，返回 agent result"""
    from pydantic_ai.usage import UsageLimits
    from src_deepagent.monitoring.langfuse_tracer import trace_span, update_current_span

    # 始终创建 Sub-Agent 配置，让主 Agent 自主决定是否委派
    sub_agent_configs = create_sub_agent_configs(
        agent_tools=decision.resources.agent_tools,
        mcp_toolsets=decision.resources.mcp_toolsets,
    )

    agent, deps = create_orchestrator_agent(
        plan=decision,
        sub_agent_configs=sub_agent_configs,
        session_id=session_id,
        trace_id=trace_id,
        publish_fn=lambda event: _publish(session_id, {**event, "session_id": session_id, "trace_id": trace_id}),
    )

    effective_query = request.query
    _ctx = {"session_id": session_id, "trace_id": trace_id}
    settings = get_settings()

    with trace_span(
        name="agent_query",
        as_type="agent",
        input={"query": request.query, "mode": str(decision.mode)},
        metadata={"session_id": session_id, "trace_id": trace_id, "mode": str(decision.mode)},
    ) as _trace:

        try:
            iter_kwargs: dict = {
                "deps": deps,
                "message_history": message_history or None,
                "usage_limits": UsageLimits(request_limit=15), # 单次 Agent 运行最多向LLM发起的请求次数
            }

            bundle = get_model_bundle("orchestrator", decision.mode.value)
            if bundle.model_settings:
                iter_kwargs["model_settings"] = bundle.model_settings

            if settings.llm.true_streaming_enabled:
                result = await agent.run(
                    effective_query,
                    **iter_kwargs,
                    event_stream_handler=_build_event_stream_handler(
                        session_id,
                        trace_id,
                        reasoning_format=bundle.profile.reasoning_format,
                    ),
                )
            else:
                async with agent.iter(effective_query, **iter_kwargs) as run:
                    from pydantic_ai._agent_graph import End

                    async for node in run:
                        if isinstance(node, End):
                            break

                    result = run.result

            update_current_span(output={"result_type": type(result.output).__name__})

        except Exception as e:
            update_current_span(level="ERROR", status_message=str(e)[:500])
            # 兜底：尝试从已有消息历史提取最后文本（Agent 可能已完成工作但最后一次 model 调用失败）
            last_text = _extract_last_text(run) if "run" in dir() else ""
            if last_text:
                logger.warning(f"Agent 执行异常但已有结果，降级提取 | session_id={session_id} error={e}")
                await _publish(session_id, {
                    "event_type": "text_stream",
                    "delta": last_text,
                    "is_final": True,
                    **_ctx,
                })
                from types import SimpleNamespace
                result = SimpleNamespace(output=last_text)
            else:
                await _publish(session_id, {
                    "event_type": "session_failed",
                    "error": str(e)[:500],
                    **_ctx,
                })
                raise

        logger.info(
            f"结果提取 | session_id={session_id} "
            f"output_type={type(result.output).__name__} "
            f"output_preview={str(result.output)[:300]}"
        )

        return result


def _build_event_stream_handler(
    session_id: str,
    trace_id: str,
    *,
    reasoning_format: str = "none",
):
    """构建真正的流式事件处理器。"""
    llm_settings = get_settings().llm
    parse_thinking_tags = reasoning_format == "inline_thinking_tags"
    in_thinking_block = False
    pending_text = ""

    async def _publish_text_delta(text: str) -> None:
        if not text or not llm_settings.stream_text_enabled:
            return
        await _publish(session_id, {
            "event_type": "text_stream",
            "delta": text,
            "is_final": False,
            "session_id": session_id,
            "trace_id": trace_id,
        })

    async def _publish_thinking_delta(text: str) -> None:
        if not text or not llm_settings.stream_thinking_enabled:
            return
        await _publish(session_id, {
            "event_type": "thinking",
            "content": text,
            "session_id": session_id,
            "trace_id": trace_id,
        })

    async def _handle_text_delta(raw_text: str) -> None:
        nonlocal in_thinking_block, pending_text
        if not raw_text:
            return
        if not parse_thinking_tags:
            await _publish_text_delta(raw_text)
            return

        pending_text += raw_text
        while pending_text:
            if in_thinking_block:
                end_idx = pending_text.find("</thinking>")
                if end_idx == -1:
                    safe_len = max(0, len(pending_text) - len("</thinking>") + 1)
                    if safe_len == 0:
                        break
                    await _publish_thinking_delta(pending_text[:safe_len])
                    pending_text = pending_text[safe_len:]
                    break
                await _publish_thinking_delta(pending_text[:end_idx])
                pending_text = pending_text[end_idx + len("</thinking>"):]
                in_thinking_block = False
            else:
                start_idx = pending_text.find("<thinking>")
                if start_idx == -1:
                    safe_len = max(0, len(pending_text) - len("<thinking>") + 1)
                    if safe_len == 0:
                        break
                    await _publish_text_delta(pending_text[:safe_len])
                    pending_text = pending_text[safe_len:]
                    break
                if start_idx > 0:
                    await _publish_text_delta(pending_text[:start_idx])
                pending_text = pending_text[start_idx + len("<thinking>"):]
                in_thinking_block = True

    async def _handler(ctx: Any, events: AsyncIterable[Any]) -> None:
        async for event in events:
            if isinstance(event, PartStartEvent):
                part = event.part
                part_kind = getattr(part, "part_kind", "")
                content = getattr(part, "content", None)
                if reasoning_format == "reasoning_content":
                    logger.info(
                        f"reasoning_content 调试 PartStart | session_id={session_id} trace_id={trace_id} "
                        f"part_kind={part_kind} part_type={type(part).__name__} "
                        f"content_preview={str(content)[:120] if content is not None else ''}"
                    )
                if llm_settings.stream_thinking_enabled and part_kind == "thinking" and content:
                    await _publish_thinking_delta(content)
                elif part_kind == "text" and isinstance(content, str) and content:
                    await _handle_text_delta(content)
            elif isinstance(event, PartDeltaEvent):
                delta = event.delta
                if reasoning_format == "reasoning_content":
                    logger.info(
                        f"reasoning_content 调试 PartDelta | session_id={session_id} trace_id={trace_id} "
                        f"delta_type={type(delta).__name__} "
                        f"delta_preview={getattr(delta, 'content_delta', None) or getattr(delta, 'args_delta', None) or ''}"
                    )
                if llm_settings.stream_thinking_enabled and isinstance(delta, ThinkingPartDelta) and delta.content_delta:
                    await _publish_thinking_delta(delta.content_delta)
                elif isinstance(delta, TextPartDelta) and delta.content_delta:
                    await _handle_text_delta(delta.content_delta)

        if parse_thinking_tags and pending_text:
            if in_thinking_block:
                await _publish_thinking_delta(pending_text)
            else:
                await _publish_text_delta(pending_text)

    return _handler


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
        await _publish(session_id, {
            "event_type": "process_update",
            "phase": "planning",
            "status": "in_progress",
            "message": "正在分析任务...",
            "session_id": session_id,
            "trace_id": trace_id,
        })

        # Stage 1: Reason
        decision = await _reasoning_engine.decide(request.query, request.mode)

        await _publish(session_id, {
            "event_type": "process_update",
            "phase": "planning",
            "status": "completed",
            "message": f"规划完成 | mode={decision.mode.value}",
            "session_id": session_id,
            "trace_id": trace_id,
        })

        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.EXECUTING)
        await _publish(session_id, {
            "event_type": "process_update",
            "phase": "executing",
            "status": "in_progress",
            "message": "正在执行...",
            "session_id": session_id,
            "trace_id": trace_id,
        })

        # 加载对话历史
        message_history = []
        if _session_manager:
            message_history = await _session_manager.load_messages(session_id)

        # Stage 2: Execute
        result = await _run_agent(decision, request, session_id, trace_id, message_history)

        # 保存对话历史
        if _session_manager and hasattr(result, "all_messages"):
            try:
                await _session_manager.save_messages(session_id, list(result.all_messages()))
            except Exception as e:
                logger.warning(f"对话历史保存失败 | session_id={session_id} error={e}")

        # 推送完成事件
        output = result.output if hasattr(result, "output") else str(result)
        answer = output if isinstance(output, str) else output.answer if hasattr(output, "answer") else str(output)
        # 确保 answer 非空
        if not answer:
            answer = _extract_last_text_from_result(result)

        # 防御性清理：移除 answer 中可能残留的 thinking 标签
        # （thinking 事件已由 EventPublishingCapability.after_model_request 发布）
        import re as _re
        answer = _re.sub(r'<thinking>.*?</thinking>\s*', '', answer, flags=_re.DOTALL).strip()

        logger.info(
            f"结果提取 | session_id={session_id} "
            f"output_type={type(output).__name__} "
            f"answer_len={len(answer)}"
        )
        await _publish(session_id, {
            "event_type": "session_completed",
            "answer": answer,
            "session_id": session_id,
            "trace_id": trace_id,
        })
        await _publish(session_id, {
            "event_type": "process_update",
            "phase": "executing",
            "status": "completed",
            "message": "执行完成",
            "session_id": session_id,
            "trace_id": trace_id,
        })

        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.COMPLETED)

        logger.info(f"编排完成 | session_id={session_id} mode={decision.mode.value}")

    except Exception as e:
        import traceback
        logger.error(f"编排失败 | session_id={session_id} error={e}\n{traceback.format_exc()}")
        await _publish(session_id, {"event_type": "session_failed", "error": str(e)})
        if _session_manager:
            await _session_manager.update_status(session_id, SessionStatus.FAILED)


async def _publish(session_id: str, event: dict[str, Any]) -> None:
    """发布事件到 Redis Stream"""
    if _stream_adapter:
        await _stream_adapter.publish(session_id, event)
