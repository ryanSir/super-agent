"""Redis Streams 事件适配器

将 A2UI 事件持久化到 Redis Stream，支持断点续传和实时尾随。
"""

# 标准库
import asyncio
import json
from datetime import datetime
from typing import AsyncIterator

# 本地模块
from src.core.dependencies import get_redis_client
from src.core.logging import get_logger

logger = get_logger(__name__)

# Redis key 模板与常量
STREAM_KEY = "stream:events:{session_id}"
SESSION_TTL = 3600       # 1 小时过期
STREAM_MAXLEN = 5000     # 每个会话最多保留事件数
XREAD_BLOCK_MS = 15000   # XREAD 阻塞等待 15 秒


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


async def publish_event(session_id: str, event: dict) -> str:
    """持久化事件到 Redis Stream

    Args:
        session_id: 会话 ID
        event: A2UI 事件帧

    Returns:
        Redis Stream entry ID
    """
    try:
        r = await get_redis_client()
        key = STREAM_KEY.format(session_id=session_id)
        data = json.dumps(event, default=_json_default, ensure_ascii=False)
        event_id = await r.xadd(
            key,
            {"data": data},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
        await r.expire(key, SESSION_TTL)
        return event_id
    except Exception as e:
        logger.warning(f"[StreamAdapter] Redis 写入失败，事件丢弃 | session_id={session_id} error={e}")
        return ""


async def get_session_events(
    session_id: str,
    last_event_id: str = "0-0",
) -> AsyncIterator[dict]:
    """订阅会话事件流，支持断点续传

    先 XRANGE 重放 last_event_id 之后的历史事件，再 XREAD 实时尾随新事件。

    Args:
        session_id: 会话 ID
        last_event_id: 上次收到的事件 ID，"0-0" 表示从头开始

    Yields:
        A2UI 事件帧（注入 _event_id 字段）
    """
    r = await get_redis_client()
    key = STREAM_KEY.format(session_id=session_id)

    # Phase 1: 重放历史事件 (XRANGE)
    range_start = "0-0" if last_event_id == "0-0" else f"({last_event_id}"
    try:
        historical = await r.xrange(key, min=range_start, max="+")
    except Exception as e:
        logger.warning(f"[StreamAdapter] XRANGE 失败 | session_id={session_id} error={e}")
        historical = []

    cursor = last_event_id
    for entry_id, fields in historical:
        event = json.loads(fields["data"])
        event["_event_id"] = entry_id
        cursor = entry_id
        yield event

        if event.get("event_type") in ("session_completed", "session_failed"):
            return

    # Phase 2: 实时尾随 (XREAD block)
    while True:
        try:
            results = await r.xread({key: cursor}, count=50, block=XREAD_BLOCK_MS)
            if not results:
                # 超时，发送心跳
                yield {
                    "event_type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                }
                continue

            for _stream_name, entries in results:
                for entry_id, fields in entries:
                    event = json.loads(fields["data"])
                    event["_event_id"] = entry_id
                    cursor = entry_id
                    yield event

                    if event.get("event_type") in ("session_completed", "session_failed"):
                        return

        except Exception as e:
            logger.warning(f"[StreamAdapter] XREAD 失败，重试 | session_id={session_id} error={e}")
            await asyncio.sleep(1)


async def cleanup_session(session_id: str) -> None:
    """清理会话事件流"""
    try:
        r = await get_redis_client()
        await r.delete(STREAM_KEY.format(session_id=session_id))
    except Exception as e:
        logger.warning(f"[StreamAdapter] 清理失败 | session_id={session_id} error={e}")
