"""记忆存储层

抽象基类 + Redis 实现。
"""

from __future__ import annotations

import abc
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.memory.schema import Fact, MemoryData, UserProfile

logger = get_logger(__name__)


class MemoryStorage(abc.ABC):
    """记忆存储抽象基类"""

    @abc.abstractmethod
    async def load(self, user_id: str) -> MemoryData:
        """加载用户记忆"""

    @abc.abstractmethod
    async def save(self, user_id: str, data: MemoryData) -> bool:
        """保存用户记忆"""

    @abc.abstractmethod
    async def delete(self, user_id: str) -> bool:
        """删除用户记忆"""


class RedisMemoryStorage(MemoryStorage):
    """基于 Redis 的记忆存储

    - Redis Hash 存储 profile
    - Redis Sorted Set 存储 facts（score=timestamp）
    """

    def __init__(self, key_prefix: str = "memory") -> None:
        self._prefix = key_prefix

    def _profile_key(self, user_id: str) -> str:
        return f"{self._prefix}:{user_id}:profile"

    def _facts_key(self, user_id: str) -> str:
        return f"{self._prefix}:{user_id}:facts"

    def _updated_key(self, user_id: str) -> str:
        return f"{self._prefix}:{user_id}:updated_at"

    async def load(self, user_id: str) -> MemoryData:
        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()

            # 加载 profile
            profile_data = await r.hgetall(self._profile_key(user_id))
            profile = UserProfile(
                work_context=profile_data.get("work_context", ""),
                personal_context=profile_data.get("personal_context", ""),
                top_of_mind=profile_data.get("top_of_mind", ""),
            ) if profile_data else UserProfile()

            # 加载 facts（按 score 降序，最新在前）
            raw_facts = await r.zrevrange(
                self._facts_key(user_id), 0, -1, withscores=True
            )
            facts = []
            for member, score in raw_facts:
                try:
                    fact_dict = json.loads(member)
                    facts.append(Fact(
                        content=fact_dict["content"],
                        created_at=datetime.fromtimestamp(score),
                        source_session_id=fact_dict.get("source_session_id", ""),
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue

            # 加载 updated_at
            updated_str = await r.get(self._updated_key(user_id))
            updated_at = (
                datetime.fromisoformat(updated_str)
                if updated_str
                else None
            )

            return MemoryData(
                profile=profile,
                facts=facts,
                updated_at=updated_at,
            )
        except Exception as e:
            logger.warning(f"[MemoryStorage] Redis 加载失败，返回空记忆 | user_id={user_id} error={e}")
            return MemoryData()

    async def save(self, user_id: str, data: MemoryData) -> bool:
        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()

            pipe = r.pipeline()

            # 保存 profile
            profile_key = self._profile_key(user_id)
            pipe.delete(profile_key)
            if data.profile:
                pipe.hset(profile_key, mapping={
                    "work_context": data.profile.work_context,
                    "personal_context": data.profile.personal_context,
                    "top_of_mind": data.profile.top_of_mind,
                })

            # 保存 facts（先清空再写入，保证一致性）
            facts_key = self._facts_key(user_id)
            pipe.delete(facts_key)
            for fact in data.facts:
                member = json.dumps({
                    "content": fact.content,
                    "source_session_id": fact.source_session_id,
                }, ensure_ascii=False)
                score = fact.created_at.timestamp()
                pipe.zadd(facts_key, {member: score})

            # 更新时间戳
            now = datetime.now()
            pipe.set(
                self._updated_key(user_id),
                now.isoformat(),
            )

            await pipe.execute()
            logger.info(f"[MemoryStorage] 记忆已保存 | user_id={user_id} facts={len(data.facts)}")
            return True
        except Exception as e:
            logger.error(f"[MemoryStorage] Redis 保存失败 | user_id={user_id} error={e}")
            return False

    async def delete(self, user_id: str) -> bool:
        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            await r.delete(
                self._profile_key(user_id),
                self._facts_key(user_id),
                self._updated_key(user_id),
            )
            return True
        except Exception as e:
            logger.error(f"[MemoryStorage] 删除失败 | user_id={user_id} error={e}")
            return False


# 全局单例
_storage: Optional[MemoryStorage] = None


def get_memory_storage() -> MemoryStorage:
    """获取记忆存储单例"""
    global _storage
    if _storage is None:
        from src.config.settings import get_settings
        settings = get_settings()
        _storage = RedisMemoryStorage(key_prefix=settings.memory.redis_key_prefix)
    return _storage
