"""记忆检索器

从 Redis 加载记忆，格式化为可注入 system prompt 的文本。
"""

from __future__ import annotations

import asyncio
from typing import Optional

from src.core.logging import get_logger

logger = get_logger(__name__)

# 检索超时（毫秒）
_RETRIEVE_TIMEOUT_MS = 200


class MemoryRetriever:
    """检索用户记忆并格式化为 prompt 文本"""

    async def retrieve(self, user_id: str) -> str:
        """检索用户记忆，格式化为 [User Context] 文本

        Args:
            user_id: 用户 ID

        Returns:
            格式化的记忆文本，无记忆时返回空字符串
        """
        # 检查是否启用
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            if not settings.memory.enabled:
                return ""
        except Exception:
            return ""

        try:
            result = await asyncio.wait_for(
                self._do_retrieve(user_id),
                timeout=_RETRIEVE_TIMEOUT_MS / 1000,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"[MemoryRetriever] 检索超时 | user_id={user_id} timeout={_RETRIEVE_TIMEOUT_MS}ms"
            )
            return ""
        except Exception as e:
            logger.warning(f"[MemoryRetriever] 检索失败 | user_id={user_id} error={e}")
            return ""

    async def _do_retrieve(self, user_id: str) -> str:
        from src.memory.storage import get_memory_storage

        storage = get_memory_storage()
        data = await storage.load(user_id)

        # 无记忆
        if not data.profile.work_context and not data.profile.personal_context and not data.facts:
            return ""

        parts = ["[User Context]"]

        # Profile
        if data.profile.work_context:
            parts.append(f"工作背景: {data.profile.work_context}")
        if data.profile.personal_context:
            parts.append(f"个人偏好: {data.profile.personal_context}")
        if data.profile.top_of_mind:
            parts.append(f"当前关注: {data.profile.top_of_mind}")

        # 最近的 facts（最多 10 条）
        if data.facts:
            parts.append("相关事实:")
            for fact in data.facts[:10]:
                parts.append(f"- {fact.content}")

        return "\n".join(parts)


# 全局单例
_retriever: Optional[MemoryRetriever] = None


def get_memory_retriever() -> MemoryRetriever:
    global _retriever
    if _retriever is None:
        _retriever = MemoryRetriever()
    return _retriever
