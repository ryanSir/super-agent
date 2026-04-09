"""记忆存储层

MemoryStorage ABC + RedisMemoryStorage 实现。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src_deepagent.core.logging import get_logger
from src_deepagent.memory.schema import Fact, MemoryData, UserProfile

logger = get_logger(__name__)


class MemoryStorage(ABC):
    """记忆存储抽象基类"""

    @abstractmethod
    async def load(self, user_id: str) -> MemoryData | None:
        """加载用户记忆"""

    @abstractmethod
    async def save_profile(self, user_id: str, profile: UserProfile) -> None:
        """保存用户画像"""

    @abstractmethod
    async def add_fact(self, user_id: str, fact: Fact) -> None:
        """添加事实"""

    @abstractmethod
    async def get_facts(self, user_id: str, limit: int = 100) -> list[Fact]:
        """获取事实列表（按时间倒序）"""


class RedisMemoryStorage(MemoryStorage):
    """Redis 记忆存储

    - Profile: Redis Hash (memory:{user_id}:profile)
    - Facts: Redis Sorted Set (memory:{user_id}:facts), score=timestamp
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def _profile_key(self, user_id: str) -> str:
        return f"memory:{user_id}:profile"

    def _facts_key(self, user_id: str) -> str:
        return f"memory:{user_id}:facts"

    async def load(self, user_id: str) -> MemoryData | None:
        """加载完整记忆"""
        profile_data = await self._redis.hgetall(self._profile_key(user_id))
        if not profile_data:
            return None

        profile = UserProfile(
            work_context=profile_data.get("work_context", ""),
            personal_context=profile_data.get("personal_context", ""),
            top_of_mind=profile_data.get("top_of_mind", ""),
        )
        facts = await self.get_facts(user_id)

        return MemoryData(user_id=user_id, profile=profile, facts=facts)

    async def save_profile(self, user_id: str, profile: UserProfile) -> None:
        """保存用户画像"""
        await self._redis.hset(
            self._profile_key(user_id),
            mapping={
                "work_context": profile.work_context,
                "personal_context": profile.personal_context,
                "top_of_mind": profile.top_of_mind,
            },
        )

    async def add_fact(self, user_id: str, fact: Fact) -> None:
        """添加事实到 Sorted Set"""
        score = fact.created_at.timestamp()
        value = json.dumps(
            {
                "content": fact.content,
                "created_at": fact.created_at.isoformat(),
                "source_session_id": fact.source_session_id,
            },
            ensure_ascii=False,
        )
        await self._redis.zadd(self._facts_key(user_id), {value: score})

    async def get_facts(self, user_id: str, limit: int = 100) -> list[Fact]:
        """获取事实（按时间倒序）"""
        raw = await self._redis.zrevrange(self._facts_key(user_id), 0, limit - 1)
        facts: list[Fact] = []
        for item in raw:
            try:
                data = json.loads(item)
                facts.append(Fact(
                    content=data["content"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    source_session_id=data.get("source_session_id", ""),
                ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"事实解析失败 | error={e}")
        return facts
