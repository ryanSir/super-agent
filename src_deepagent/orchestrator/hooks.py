"""Hooks — 基于 pydantic-deep 框架的生命周期钩子

将事件推送、循环检测、安全审计等能力以 Hook(event, handler) 形式注册到 Agent，
由框架在工具调用 / LLM 请求 / Agent 运行等生命周期节点自动触发。
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from typing import Any, Callable

from pydantic_deep.capabilities.hooks import Hook, HookEvent, HookInput, HookResult

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


# ── 事件推送 Hooks ─────────────────────────────────────────


def create_event_push_hooks(publish_fn: Callable | None = None) -> list[Hook]:
    """工具调用事件推送到 Redis Stream → SSE → 前端

    Args:
        publish_fn: 已绑定 session_id 的事件发布函数，签名 async def(event: dict)
    """

    async def on_tool_call(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: PRE_TOOL_USE [EventPush] | tool={inp.tool_name} <<<<<<")
        # NOTE: 暂不推送事件，避免与 rest_api._execute_plan() 中的推送重复
        # 后续清理 rest_api 冗余推送后再启用
        return HookResult(allow=True)

    async def on_tool_result(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: POST_TOOL_USE [EventPush] | tool={inp.tool_name} <<<<<<")
        return HookResult()

    async def on_tool_failure(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: POST_TOOL_USE_FAILURE [EventPush] | tool={inp.tool_name} <<<<<<")
        return HookResult()

    return [
        Hook(event=HookEvent.PRE_TOOL_USE, handler=on_tool_call, background=True),
        Hook(event=HookEvent.POST_TOOL_USE, handler=on_tool_result, background=True),
        Hook(event=HookEvent.POST_TOOL_USE_FAILURE, handler=on_tool_failure, background=True),
    ]


# ── 循环检测 Hooks ─────────────────────────────────────────

_DEFAULT_WINDOW_SIZE = 20
_WARN_THRESHOLD = 3
_HARD_LIMIT = 5


def create_loop_detection_hooks(
    window_size: int = _DEFAULT_WINDOW_SIZE,
    warn_threshold: int = _WARN_THRESHOLD,
    hard_limit: int = _HARD_LIMIT,
) -> list[Hook]:
    """循环检测：滑动窗口 + MD5 去重 + 警告 + 强制拒绝

    Args:
        window_size: 滑动窗口大小
        warn_threshold: 警告阈值（同一指纹出现次数）
        hard_limit: 强制拒绝阈值
    """
    call_hashes: deque[str] = deque(maxlen=window_size)
    hash_counts: dict[str, int] = {}

    async def detect_loop(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: PRE_TOOL_USE [LoopDetection] | tool={inp.tool_name} <<<<<<")
        fingerprint = hashlib.md5(
            f"{inp.tool_name}:{inp.tool_input}".encode()
        ).hexdigest()

        # 滑动窗口驱逐
        if len(call_hashes) >= window_size:
            evicted = call_hashes[0]
            hash_counts[evicted] = max(0, hash_counts.get(evicted, 0) - 1)
            if hash_counts[evicted] == 0:
                hash_counts.pop(evicted, None)

        call_hashes.append(fingerprint)
        hash_counts[fingerprint] = hash_counts.get(fingerprint, 0) + 1

        count = hash_counts[fingerprint]

        if count >= hard_limit:
            logger.error(
                f"循环检测: 强制拒绝 | tool={inp.tool_name} count={count}/{hard_limit}"
            )
            return HookResult(
                allow=False,
                reason=f"工具 '{inp.tool_name}' 在滑动窗口内被调用 {count} 次，强制停止",
            )

        if count >= warn_threshold:
            logger.warning(
                f"循环检测: 警告 | tool={inp.tool_name} count={count}/{hard_limit}"
            )

        return HookResult(allow=True)

    async def reset_on_run(_inp: HookInput) -> HookResult:
        """每次 Agent 运行开始时重置检测状态"""
        # logger.info(">>>>>> HOOK FIRED: BEFORE_RUN [LoopDetection] | resetting state <<<<<<")
        call_hashes.clear()
        hash_counts.clear()
        return HookResult()

    return [
        Hook(event=HookEvent.PRE_TOOL_USE, handler=detect_loop),
        Hook(event=HookEvent.BEFORE_RUN, handler=reset_on_run),
    ]


# ── 安全审计 Hooks ─────────────────────────────────────────


def create_audit_hooks() -> list[Hook]:
    """安全审计日志：工具名 / 参数 / 耗时 / 结果"""
    call_start_times: dict[str, float] = {}

    async def log_call(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: PRE_TOOL_USE [AuditLogger] | tool={inp.tool_name} <<<<<<")
        call_start_times[inp.tool_name] = time.monotonic()
        logger.info(
            f"[AUDIT] 工具调用开始 | tool={inp.tool_name} "
            f"args={str(inp.tool_input)[:200]}"
        )
        return HookResult(allow=True)

    async def log_result(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: POST_TOOL_USE [AuditLogger] | tool={inp.tool_name} <<<<<<")
        start = call_start_times.pop(inp.tool_name, None)
        elapsed = f"{time.monotonic() - start:.2f}s" if start else "unknown"
        logger.info(
            f"[AUDIT] 工具调用完成 | tool={inp.tool_name} "
            f"elapsed={elapsed} "
            f"result={str(inp.tool_result)[:300] if inp.tool_result else ''}"
        )
        return HookResult()

    async def log_failure(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: POST_TOOL_USE_FAILURE [AuditLogger] | tool={inp.tool_name} <<<<<<")
        start = call_start_times.pop(inp.tool_name, None)
        elapsed = f"{time.monotonic() - start:.2f}s" if start else "unknown"
        logger.error(
            f"[AUDIT] 工具调用失败 | tool={inp.tool_name} "
            f"elapsed={elapsed} "
            f"error={str(inp.tool_error)[:300] if inp.tool_error else ''}"
        )
        return HookResult()

    return [
        Hook(event=HookEvent.PRE_TOOL_USE, handler=log_call),
        Hook(event=HookEvent.POST_TOOL_USE, handler=log_result),
        Hook(event=HookEvent.POST_TOOL_USE_FAILURE, handler=log_failure),
    ]


# ── Token 用量追踪 Hooks ──────────────────────────────────


def create_token_tracker_hooks() -> list[Hook]:
    """Token 用量追踪（每次 LLM 调用后记录）"""

    async def track_tokens(inp: HookInput) -> HookResult:
        # logger.info(f">>>>>> HOOK FIRED: AFTER_MODEL_REQUEST [TokenTracker] | event={inp.event} <<<<<<")
        return HookResult()

    return [
        Hook(event=HookEvent.AFTER_MODEL_REQUEST, handler=track_tokens),
    ]


# ── 工厂函数 ───────────────────────────────────────────────


def create_hooks(publish_fn: Callable | None = None) -> list[Hook]:
    """创建所有 Hook 实例（pydantic-deep 框架格式）

    Args:
        publish_fn: 已绑定 session_id 的事件发布函数，签名 async def(event: dict)。
                    传 None 则事件推送 hooks 不生效。

    Returns:
        Hook 实例列表，可直接传入 create_deep_agent(hooks=...)
    """
    hooks: list[Hook] = []
    hooks.extend(create_event_push_hooks(publish_fn))
    hooks.extend(create_loop_detection_hooks())
    hooks.extend(create_audit_hooks())
    hooks.extend(create_token_tracker_hooks())
    return hooks
