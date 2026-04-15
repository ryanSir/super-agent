"""Hooks — 基于 pydantic-deep 框架的生命周期钩子

循环检测、安全审计等能力以 Hook(event, handler) 形式注册到 Agent，
由框架在工具调用 / Agent 运行等生命周期节点自动触发。

事件发布由 EventPublishingCapability 负责，Token 追踪由 CostTracking capability 负责。
"""

from __future__ import annotations

import hashlib
import time
from collections import deque

from pydantic_deep.capabilities.hooks import Hook, HookEvent, HookInput, HookResult

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


# ── 循环检测 Hooks ─────────────────────────────────────────


def create_loop_detection_hooks(
    window_size: int = 20,
    warn_threshold: int = 3,
    hard_limit: int = 5,
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
    call_start_times: dict[str, list[float]] = {}

    async def log_call(inp: HookInput) -> HookResult:
        call_start_times.setdefault(inp.tool_name, []).append(time.monotonic())
        logger.info(
            f"[AUDIT] 工具调用开始 | tool={inp.tool_name} "
            f"args={str(inp.tool_input)[:200]}"
        )
        return HookResult(allow=True)

    async def log_result(inp: HookInput) -> HookResult:
        starts = call_start_times.get(inp.tool_name, [])
        start = starts.pop(0) if starts else None
        elapsed = f"{time.monotonic() - start:.2f}s" if start else "unknown"
        logger.info(
            f"[AUDIT] 工具调用完成 | tool={inp.tool_name} "
            f"elapsed={elapsed} "
            f"result={str(inp.tool_result)[:300] if inp.tool_result else ''}"
        )
        return HookResult()

    async def log_failure(inp: HookInput) -> HookResult:
        starts = call_start_times.get(inp.tool_name, [])
        start = starts.pop(0) if starts else None
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


# ── 工厂函数 ───────────────────────────────────────────────


def create_hooks() -> list[Hook]:
    """创建所有 Hook 实例（pydantic-deep 框架格式）

    从 HooksSettings 读取配置，按开关决定是否注册各类 hook。

    Returns:
        Hook 实例列表，可直接传入 create_deep_agent(hooks=...)
    """
    from src_deepagent.config.settings import get_settings

    settings = get_settings().hooks

    hooks: list[Hook] = []
    hooks.extend(create_loop_detection_hooks(
        window_size=settings.loop_window_size,
        warn_threshold=settings.loop_warn_threshold,
        hard_limit=settings.loop_hard_limit,
    ))
    if settings.audit_enabled:
        hooks.extend(create_audit_hooks())
    return hooks
