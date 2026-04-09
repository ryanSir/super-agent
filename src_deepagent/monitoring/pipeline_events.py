"""管道事件 — 步骤计时与元数据

提供 pipeline_step 上下文管理器，记录每个步骤的耗时和状态。
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def pipeline_step(
    step_name: str,
    metadata: dict[str, Any] | None = None,
    session_id: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """管道步骤上下文管理器

    自动记录步骤的开始、完成/失败状态和耗时。

    Usage:
        async with pipeline_step("rag_search", session_id="abc") as ctx:
            result = await do_something()
            ctx["result_count"] = len(result)
    """
    ctx: dict[str, Any] = {"step_name": step_name, **(metadata or {})}
    start = time.monotonic()

    logger.info(f"[Pipeline] {step_name} 开始 | session_id={session_id}")

    try:
        yield ctx
        elapsed = time.monotonic() - start
        logger.info(
            f"[Pipeline] {step_name} 完成 | "
            f"elapsed={elapsed:.2f}s session_id={session_id}"
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(
            f"[Pipeline] {step_name} 失败 | "
            f"error={e} elapsed={elapsed:.2f}s session_id={session_id}"
        )
        raise
