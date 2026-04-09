"""记忆检索

从 Redis 检索用户记忆，200ms 超时降级。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.memory.schema import MemoryData
from src_deepagent.memory.storage import RedisMemoryStorage

logger = get_logger(__name__)


class MemoryRetriever:
    """记忆检索器"""

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._storage: RedisMemoryStorage | None = None

    def _get_storage(self) -> RedisMemoryStorage:
        if self._storage is None:
            if self._redis is None:
                raise RuntimeError("Redis 客户端未初始化")
            self._storage = RedisMemoryStorage(self._redis)
        return self._storage

    async def retrieve(self, user_id: str) -> str:
        """检索用户记忆，格式化为文本

        200ms 超时降级：超时返回空字符串。

        Args:
            user_id: 用户 ID

        Returns:
            格式化的记忆文本，失败返回空字符串
        """
        settings = get_settings()
        timeout_s = settings.memory.retrieval_timeout_ms / 1000.0

        try:
            memory = await asyncio.wait_for(
                self._load(user_id),
                timeout=timeout_s,
            )
            if not memory:
                return ""
            return self._format(memory)
        except asyncio.TimeoutError:
            logger.warning(f"记忆检索超时 | user_id={user_id} timeout={timeout_s}s")
            return ""
        except Exception as e:
            logger.warning(f"记忆检索失败 | user_id={user_id} error={e}")
            return ""

    async def _load(self, user_id: str) -> MemoryData | None:
        storage = self._get_storage()
        return await storage.load(user_id)

    def _format(self, memory: MemoryData) -> str:
        """格式化记忆为文本块"""
        parts: list[str] = ["[用户上下文]"]

        p = memory.profile
        if p.work_context:
            parts.append(f"工作: {p.work_context}")
        if p.personal_context:
            parts.append(f"偏好: {p.personal_context}")
        if p.top_of_mind:
            parts.append(f"关注: {p.top_of_mind}")

        if memory.facts:
            parts.append("\n已知事实:")
            for fact in memory.facts[:20]:
                parts.append(f"- {fact.content}")

        return "\n".join(parts)
