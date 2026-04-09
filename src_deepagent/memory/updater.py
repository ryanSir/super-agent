"""记忆更新

LLM 抽取事实 + 分布式锁 + 去重。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.memory.schema import Fact, UserProfile
from src_deepagent.memory.storage import RedisMemoryStorage

logger = get_logger(__name__)

_LOCK_PREFIX = "memory:lock:"


class MemoryUpdater:
    """记忆更新器"""

    def __init__(self, redis_client: Any, llm_fn: Any = None) -> None:
        self._redis = redis_client
        self._storage = RedisMemoryStorage(redis_client)
        self._llm_fn = llm_fn  # async def llm_fn(prompt: str) -> str

    async def update(
        self,
        user_id: str,
        query: str,
        answer: str,
        session_id: str = "",
    ) -> None:
        """从对话中抽取记忆并更新

        Args:
            user_id: 用户 ID
            query: 用户查询
            answer: Agent 回答
            session_id: 会话 ID
        """
        settings = get_settings()
        if not settings.memory.enabled:
            return

        lock_key = f"{_LOCK_PREFIX}{user_id}"

        # 分布式锁（防止并发更新）
        acquired = await self._redis.set(
            lock_key, "1", ex=settings.memory.lock_ttl, nx=True
        )
        if not acquired:
            logger.info(f"记忆更新跳过（锁冲突）| user_id={user_id}")
            return

        try:
            await self._do_update(user_id, query, answer, session_id)
        finally:
            await self._redis.delete(lock_key)

    async def _do_update(
        self,
        user_id: str,
        query: str,
        answer: str,
        session_id: str,
    ) -> None:
        """执行更新（锁内）"""
        if not self._llm_fn:
            return

        # 并行抽取 profile 和 facts
        profile_task = self._extract_profile(query, answer)
        facts_task = self._extract_facts(query, answer)

        profile_update, new_facts = await asyncio.gather(
            profile_task, facts_task, return_exceptions=True
        )

        # 更新 profile
        if isinstance(profile_update, UserProfile):
            await self._storage.save_profile(user_id, profile_update)

        # 添加 facts（去重）
        if isinstance(new_facts, list):
            existing = await self._storage.get_facts(user_id)
            existing_contents = {f.content for f in existing}

            added = 0
            for fact_text in new_facts:
                if fact_text not in existing_contents:
                    fact = Fact(content=fact_text, source_session_id=session_id)
                    await self._storage.add_fact(user_id, fact)
                    added += 1

            # 保留上限
            settings = get_settings()
            all_facts = await self._storage.get_facts(user_id, limit=settings.memory.max_facts + 50)
            if len(all_facts) > settings.memory.max_facts:
                # TODO: 驱逐最旧的 facts
                pass

            if added:
                logger.info(f"记忆更新 | user_id={user_id} new_facts={added}")

    async def _extract_profile(self, query: str, answer: str) -> UserProfile:
        """LLM 抽取用户画像更新"""
        prompt = (
            f"从以下对话中提取用户画像信息。\n\n"
            f"用户: {query}\n助手: {answer[:500]}\n\n"
            f"输出 JSON: {{\"work_context\": \"\", \"personal_context\": \"\", \"top_of_mind\": \"\"}}"
        )
        try:
            result = await self._llm_fn(prompt)
            data = json.loads(result)
            return UserProfile(**data)
        except Exception:
            return UserProfile()

    async def _extract_facts(self, query: str, answer: str) -> list[str]:
        """LLM 抽取事实"""
        prompt = (
            f"从以下对话中提取值得记住的事实（最多5条）。\n\n"
            f"用户: {query}\n助手: {answer[:500]}\n\n"
            f"输出 JSON 数组: [\"事实1\", \"事实2\"]"
        )
        try:
            result = await self._llm_fn(prompt)
            return json.loads(result)
        except Exception:
            return []
