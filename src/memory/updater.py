"""记忆更新器

使用 LLM 从对话中提取用户画像和事实，写入存储。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.memory.prompts import FACT_EXTRACTION_PROMPT, PROFILE_UPDATE_PROMPT
from src.memory.schema import Fact, MemoryData

logger = get_logger(__name__)

# Redis 分布式锁 key 模板
_LOCK_KEY = "memory:lock:{user_id}"
_LOCK_TTL = 30  # 秒


class MemoryUpdater:
    """从对话中提取记忆并更新存储"""

    def __init__(self, max_facts: int = 100, model_alias: str = "fast") -> None:
        self._max_facts = max_facts
        self._model_alias = model_alias

    async def update(
        self,
        user_id: str,
        messages: list,
        session_id: str = "",
    ) -> bool:
        """从对话中提取记忆并更新

        Args:
            user_id: 用户 ID
            messages: 过滤后的对话消息
            session_id: 来源会话 ID

        Returns:
            是否更新成功
        """
        from src.memory.storage import get_memory_storage

        storage = get_memory_storage()

        # 获取分布式锁
        lock = await self._acquire_lock(user_id)
        if not lock:
            logger.warning(f"[MemoryUpdater] 获取锁失败，跳过更新 | user_id={user_id}")
            return False

        try:
            # 加载现有记忆
            current = await storage.load(user_id)

            # 提取对话文本
            conversation = self._format_conversation(messages)
            if not conversation.strip():
                return False

            # 并行提取 profile 更新和新 facts
            profile_task = self._extract_profile_update(conversation, current)
            facts_task = self._extract_facts(conversation, session_id)

            profile_update, new_facts = await asyncio.gather(
                profile_task, facts_task, return_exceptions=True
            )

            updated = False

            # 更新 profile
            if isinstance(profile_update, dict) and profile_update:
                for key, value in profile_update.items():
                    if value and hasattr(current.profile, key):
                        setattr(current.profile, key, value)
                        updated = True

            # 添加新 facts（去重 + 上限淘汰）
            if isinstance(new_facts, list) and new_facts:
                existing_contents = {
                    f.content.strip() for f in current.facts
                }
                for fact in new_facts:
                    content = fact.content.strip()
                    if content in existing_contents:
                        # 更新已有 fact 的时间戳
                        for f in current.facts:
                            if f.content.strip() == content:
                                f.created_at = datetime.now()
                                updated = True
                                break
                    else:
                        current.facts.append(fact)
                        existing_contents.add(content)
                        updated = True

                # 按时间排序，淘汰最旧的
                if len(current.facts) > self._max_facts:
                    current.facts.sort(key=lambda f: f.created_at, reverse=True)
                    current.facts = current.facts[:self._max_facts]

            if updated:
                current.updated_at = datetime.now()
                await storage.save(user_id, current)
                logger.info(
                    f"[MemoryUpdater] 记忆已更新 | "
                    f"user_id={user_id} facts={len(current.facts)}"
                )

                # 推送事件
                await self._publish_update_event(
                    session_id, user_id, new_facts
                )

            return updated
        except Exception as e:
            logger.error(f"[MemoryUpdater] 更新失败 | user_id={user_id} error={e}")
            return False
        finally:
            await self._release_lock(user_id, lock)

    def _format_conversation(self, messages: list) -> str:
        """将消息列表格式化为文本"""
        parts = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                parts.append(f"{role}: {content}")
            elif hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "content"):
                        parts.append(str(part.content))
        return "\n".join(parts)

    async def _extract_profile_update(
        self, conversation: str, current: MemoryData
    ) -> Dict[str, str]:
        """用 LLM 提取 profile 更新"""
        try:
            from pydantic_ai import Agent
            from src.llm.config import get_model

            agent = Agent(
                model=get_model(self._model_alias),
                output_type=dict,
                instructions=PROFILE_UPDATE_PROMPT,
            )

            prompt = (
                f"当前用户画像:\n"
                f"- work_context: {current.profile.work_context}\n"
                f"- personal_context: {current.profile.personal_context}\n"
                f"- top_of_mind: {current.profile.top_of_mind}\n\n"
                f"最新对话:\n{conversation[:4000]}"
            )

            result = await agent.run(prompt)
            return result.output if isinstance(result.output, dict) else {}
        except Exception as e:
            logger.warning(f"[MemoryUpdater] profile 提取失败 | error={e}")
            return {}

    async def _extract_facts(
        self, conversation: str, session_id: str
    ) -> List[Fact]:
        """用 LLM 提取新事实"""
        try:
            from pydantic_ai import Agent
            from src.llm.config import get_model

            agent = Agent(
                model=get_model(self._model_alias),
                output_type=list,
                instructions=FACT_EXTRACTION_PROMPT,
            )

            result = await agent.run(conversation[:4000])
            facts = []
            if isinstance(result.output, list):
                for item in result.output:
                    content = item if isinstance(item, str) else str(item)
                    if content.strip():
                        facts.append(Fact(
                            content=content.strip(),
                            source_session_id=session_id,
                        ))
            return facts
        except Exception as e:
            logger.warning(f"[MemoryUpdater] facts 提取失败 | error={e}")
            return []

    async def _acquire_lock(self, user_id: str) -> Optional[str]:
        """获取 Redis 分布式锁"""
        try:
            import uuid
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            lock_value = uuid.uuid4().hex
            acquired = await r.set(
                _LOCK_KEY.format(user_id=user_id),
                lock_value,
                nx=True,
                ex=_LOCK_TTL,
            )
            return lock_value if acquired else None
        except Exception:
            return None

    async def _release_lock(self, user_id: str, lock_value: str) -> None:
        """释放 Redis 分布式锁"""
        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            key = _LOCK_KEY.format(user_id=user_id)
            current = await r.get(key)
            if current == lock_value:
                await r.delete(key)
        except Exception:
            pass

    async def _publish_update_event(
        self,
        session_id: str,
        user_id: str,
        new_facts: Any,
    ) -> None:
        """推送记忆更新事件"""
        try:
            from src.streaming.stream_adapter import publish_event
            fact_count = len(new_facts) if isinstance(new_facts, list) else 0
            await publish_event(session_id, {
                "event_type": "memory_update",
                "user_id": user_id,
                "update_type": "fact" if fact_count > 0 else "profile",
                "summary": f"更新了 {fact_count} 条事实记录",
            })
        except Exception:
            pass
