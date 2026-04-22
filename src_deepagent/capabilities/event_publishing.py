"""EventPublishingCapability — 统一事件发布

基于 AbstractCapability 的自定义 Capability，通过生命周期方法拦截
工具调用、LLM 响应、Agent 运行等事件，统一发布到 Redis Stream → SSE → 前端。

替代：
- rest_api.py 中 _run_agent() 的内联事件推送
- base_tools.py 中 _wrap_with_tool_result() + ContextVar 模式
- hooks.py 中被禁用的 event push hooks
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic_ai.capabilities import AbstractCapability

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


def _infer_tool_type(tool_name: str) -> str:
    """根据工具名推断工具类型"""
    _SANDBOX_TOOLS = {"execute_sandbox", "run_code", "execute_code"}
    _NATIVE_TOOLS = {
        "emit_chart", "plan_and_decompose",
        "search_skills", "list_skills", "create_skill", "baidu_search",
    }
    _BUILTIN_TOOLS = {
        "write_todos", "read_todos", "update_todo_status",
        "task", "wait_task", "delegate_to_subagent",
        "context_summary", "checkpoint", "restore_checkpoint",
    }

    if tool_name in _SANDBOX_TOOLS:
        return "sandbox"
    if tool_name in _NATIVE_TOOLS:
        return "native_worker"
    if tool_name == "execute_skill":
        return "skill"
    if tool_name in _BUILTIN_TOOLS:
        return "builtin"
    try:
        from src_deepagent.capabilities.skills.registry import skill_registry
        if tool_name in skill_registry._skills:
            return "skill"
    except Exception:
        pass
    return "mcp"


@dataclass
class EventPublishingCapability(AbstractCapability[Any]):
    """统一事件发布 Capability

    通过 wrap_tool_execute / after_model_request / after_run 拦截事件，
    发布 tool_call、tool_result、thinking、text_stream、render_widget 到 Redis Stream。
    """

    publish_fn: Callable[..., Any] | None = None
    session_id: str = ""
    trace_id: str = ""

    # per-run 状态
    _reported_tool_ids: set[str] = field(default_factory=set, init=False)

    @property
    def _ctx(self) -> dict[str, str]:
        return {"session_id": self.session_id, "trace_id": self.trace_id}

    async def _publish(self, event: dict[str, Any]) -> None:
        """安全发布事件，publish_fn 为 None 时静默跳过"""
        if not self.publish_fn:
            return
        try:
            await self.publish_fn(event)
        except Exception as e:
            logger.warning(f"事件发布失败 | event_type={event.get('event_type')} error={e}")

    # ── Run 生命周期 ──────────────────────────────────────

    async def before_run(self, ctx: Any) -> None:
        """重置 per-run 状态"""
        self._reported_tool_ids = set()

    async def after_run(self, ctx: Any, *, result: Any) -> Any:
        """发布流终止标记"""
        await self._publish({
            "event_type": "text_stream",
            "delta": "",
            "is_final": True,
            **self._ctx,
        })
        return result

    # ── Tool 生命周期 ─────────────────────────────────────

    async def wrap_tool_execute(
        self,
        ctx: Any,
        *,
        call: Any,
        tool_def: Any,
        args: Any,
        handler: Any,
    ) -> Any:
        """包装工具执行：发布 tool_call + Langfuse span + 计时"""
        tool_name = call.tool_name
        tool_call_id = getattr(call, "tool_call_id", None) or f"_call_{uuid.uuid4().hex[:8]}"

        # 发布 tool_call 事件
        await self._publish({
            "event_type": "tool_call",
            "tool_name": tool_name,
            "display_name": tool_name,
            "tool_type": _infer_tool_type(tool_name),
            "args": str(getattr(call, "args", args))[:200],
            **self._ctx,
        })

        # Langfuse span + 执行
        from src_deepagent.monitoring.langfuse_tracer import trace_span, update_current_span

        start = time.monotonic()
        with trace_span(
            name=f"tool_{tool_name}",
            as_type="tool",
            input={"args": str(args)[:500]},
            metadata={"tool_type": _infer_tool_type(tool_name)},
        ) as _span:
            result = await handler(args)
            elapsed = time.monotonic() - start

            # 更新 Langfuse span
            if isinstance(result, dict):
                status = "success" if result.get("success", True) else "failed"
                if status == "failed":
                    update_current_span(
                        output=result,
                        level="ERROR",
                        status_message=str(result.get("error", ""))[:500],
                    )
                else:
                    update_current_span(output=result)
            else:
                update_current_span(output={"result": str(result)[:500]})

        # 发布 tool_result 事件（去重）
        if tool_call_id not in self._reported_tool_ids:
            self._reported_tool_ids.add(tool_call_id)

            if isinstance(result, dict):
                status = "success" if result.get("success", True) else "failed"
                content = str(result.get("data", result.get("error", "")))
            else:
                status = "success"
                content = str(result)

            await self._publish({
                "event_type": "tool_result",
                "tool_name": tool_name,
                "tool_type": _infer_tool_type(tool_name),
                "status": status,
                "content": content,
                **self._ctx,
            })

            # emit_chart 特殊处理：额外推送 render_widget
            if tool_name == "emit_chart" and isinstance(result, dict) and result.get("success"):
                data = result.get("data", {})
                await self._publish({
                    "event_type": "render_widget",
                    "widget_id": data.get("widget_id", f"chart-{uuid.uuid4().hex[:8]}"),
                    "ui_component": data.get("ui_component", "DataChart"),
                    "props": data.get("props", {}),
                    **self._ctx,
                })

        return result

    async def on_tool_execute_error(
        self,
        ctx: Any,
        *,
        call: Any,
        tool_def: Any,
        args: Any,
        error: Exception,
    ) -> Any:
        """工具执行失败：发布 error 状态的 tool_result + 更新 Langfuse span"""
        tool_name = call.tool_name

        from src_deepagent.monitoring.langfuse_tracer import update_current_span
        update_current_span(
            level="ERROR",
            status_message=str(error)[:500],
        )

        await self._publish({
            "event_type": "tool_result",
            "tool_name": tool_name,
            "tool_type": _infer_tool_type(tool_name),
            "status": "error",
            "content": str(error)[:500],
            **self._ctx,
        })

        raise error

    # ── Model Request 生命周期 ────────────────────────────

    async def after_model_request(
        self,
        ctx: Any,
        *,
        request_context: Any,
        response: Any,
    ) -> Any:
        """从 LLM 响应中提取 thinking 和 text_stream 事件"""
        llm_settings = get_settings().llm
        if llm_settings.true_streaming_enabled:
            return response

        if not hasattr(response, "parts"):
            return response

        for part in response.parts:
            part_kind = getattr(part, "part_kind", "")

            # thinking 事件
            if (
                llm_settings.stream_thinking_enabled
                and part_kind == "thinking"
                and hasattr(part, "content")
                and part.content
            ):
                await self._publish({
                    "event_type": "thinking",
                    "content": part.content,
                    **self._ctx,
                })

            # text_stream 事件
            elif (
                llm_settings.stream_text_enabled
                and hasattr(part, "content")
                and isinstance(part.content, str)
                and part.content
            ):
                # 跳过 tool_call 类型的 part
                if part_kind not in ("tool-call", "tool-return", "thinking"):
                    await self._publish({
                        "event_type": "text_stream",
                        "delta": part.content,
                        "is_final": False,
                        **self._ctx,
                    })

        return response
