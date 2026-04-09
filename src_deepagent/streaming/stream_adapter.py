"""Redis Streams 适配器

封装 XADD/XRANGE/XREAD 操作，支持事件发布和消费。
"""

from __future__ import annotations

import json
import time
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


class StreamAdapter:
    """Redis Streams 事件适配器"""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def _stream_key(self, session_id: str) -> str:
        return f"stream:{session_id}"

    async def publish(self, session_id: str, event: dict[str, Any]) -> str:
        """发布事件到 Redis Stream

        Args:
            session_id: 会话 ID
            event: 事件数据

        Returns:
            事件 ID
        """
        settings = get_settings()
        key = self._stream_key(session_id)

        payload = {
            "data": json.dumps(event, ensure_ascii=False, default=str),
            "timestamp": str(time.time()),
        }

        event_id = await self._redis.xadd(
            key,
            payload,
            maxlen=settings.redis.stream_max_len,
        )

        # 设置 TTL
        await self._redis.expire(key, settings.redis.stream_ttl)

        return event_id

    async def read(
        self,
        session_id: str,
        last_id: str = "0-0",
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """从 Redis Stream 读取事件

        Args:
            session_id: 会话 ID
            last_id: 上次读取的事件 ID（用于断点续传）
            count: 最大读取数量

        Returns:
            事件列表
        """
        key = self._stream_key(session_id)
        raw = await self._redis.xrange(key, min=last_id, count=count)

        events: list[dict[str, Any]] = []
        for event_id, fields in raw:
            # 跳过 last_id 本身
            if event_id == last_id:
                continue
            try:
                data = json.loads(fields.get("data", "{}"))
                data["_event_id"] = event_id
                events.append(data)
            except json.JSONDecodeError:
                pass

        return events

    async def read_blocking(
        self,
        session_id: str,
        last_id: str = "$",
        block_ms: int = 5000,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """阻塞读取新事件

        Args:
            session_id: 会话 ID
            last_id: 起始 ID（$ 表示只读新消息）
            block_ms: 阻塞等待毫秒数
            count: 最大读取数量

        Returns:
            事件列表
        """
        key = self._stream_key(session_id)
        result = await self._redis.xread(
            {key: last_id},
            block=block_ms,
            count=count,
        )

        events: list[dict[str, Any]] = []
        if result:
            for _stream_name, messages in result:
                for event_id, fields in messages:
                    try:
                        data = json.loads(fields.get("data", "{}"))
                        data["_event_id"] = event_id
                        events.append(data)
                    except json.JSONDecodeError:
                        pass

        return events
