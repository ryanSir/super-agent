"""SSE 端点

Server-Sent Events 流式推送，支持断点续传（Last-Event-ID）和心跳。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

from src_deepagent.core.logging import get_logger
from src_deepagent.streaming.stream_adapter import StreamAdapter

logger = get_logger(__name__)

_HEARTBEAT_INTERVAL = 15  # 秒


async def sse_event_generator(
    stream_adapter: StreamAdapter,
    session_id: str,
    last_event_id: str = "0-0",
) -> AsyncGenerator[str, None]:
    """SSE 事件生成器

    Args:
        stream_adapter: Redis Streams 适配器
        session_id: 会话 ID
        last_event_id: 断点续传的起始事件 ID

    Yields:
        SSE 格式的事件字符串
    """
    cursor = last_event_id
    last_heartbeat = time.monotonic()

    while True:
        # 尝试读取新事件
        events = await stream_adapter.read(session_id, last_id=cursor, count=50)

        if events:
            for event in events:
                event_id = event.pop("_event_id", "")
                event_type = event.get("event_type", "message")
                data = json.dumps(event, ensure_ascii=False, default=str)

                yield f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"

                if event_id:
                    cursor = event_id

                # 检查是否结束
                if event_type in ("session_completed", "session_failed"):
                    return

            last_heartbeat = time.monotonic()
        else:
            # 无新事件，检查是否需要心跳
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                yield f"event: heartbeat\ndata: {{}}\n\n"
                last_heartbeat = now

            # 短暂等待后重试
            await asyncio.sleep(0.5)
