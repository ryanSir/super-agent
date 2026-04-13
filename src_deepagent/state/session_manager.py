"""会话状态管理

Redis 持久化 + 状态机（CREATED → PLANNING → EXECUTING → COMPLETED/FAILED）。
"""

from __future__ import annotations

import json
import time
from typing import Any

from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import SessionStatus

logger = get_logger(__name__)

# 合法的状态转换
_VALID_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.CREATED: {SessionStatus.PLANNING, SessionStatus.EXECUTING, SessionStatus.FAILED},
    SessionStatus.PLANNING: {SessionStatus.EXECUTING, SessionStatus.FAILED, SessionStatus.TIMEOUT},
    SessionStatus.EXECUTING: {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.TIMEOUT},
    SessionStatus.COMPLETED: set(),
    SessionStatus.FAILED: set(),
    SessionStatus.TIMEOUT: set(),
}


class Session:
    """会话实例"""

    __slots__ = ("session_id", "trace_id", "query", "status", "created_at", "metadata")

    def __init__(
        self,
        session_id: str,
        trace_id: str,
        query: str,
        status: SessionStatus = SessionStatus.CREATED,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session_id = session_id
        self.trace_id = trace_id
        self.query = query
        self.status = status
        self.created_at = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "query": self.query,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": json.dumps(self.metadata, ensure_ascii=False),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        metadata = data.get("metadata", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return cls(
            session_id=data["session_id"],
            trace_id=data.get("trace_id", ""),
            query=data.get("query", ""),
            status=SessionStatus(data.get("status", "created")),
            metadata=metadata,
        )


class SessionManager:
    """会话管理器 — Redis 持久化"""

    _TTL = 3600  # 1 小时

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._local: dict[str, Session] = {}  # 内存缓存

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        return f"conversation:{session_id}:messages"

    async def create(
        self,
        session_id: str,
        trace_id: str,
        query: str,
    ) -> Session:
        """创建会话"""
        session = Session(session_id=session_id, trace_id=trace_id, query=query)
        self._local[session_id] = session

        if self._redis:
            await self._redis.hset(self._key(session_id), mapping=session.to_dict())
            await self._redis.expire(self._key(session_id), self._TTL)

        logger.info(f"会话创建 | session_id={session_id} trace_id={trace_id}")
        return session

    async def get(self, session_id: str) -> Session | None:
        """获取会话"""
        # 先查内存
        if session_id in self._local:
            return self._local[session_id]

        # 再查 Redis
        if self._redis:
            data = await self._redis.hgetall(self._key(session_id))
            if data:
                session = Session.from_dict(data)
                self._local[session_id] = session
                return session

        return None

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """更新会话状态（带状态机校验）"""
        session = await self.get(session_id)
        if not session:
            logger.warning(f"会话不存在 | session_id={session_id}")
            return

        # 状态转换校验
        valid = _VALID_TRANSITIONS.get(session.status, set())
        if status not in valid:
            logger.warning(
                f"非法状态转换 | session_id={session_id} "
                f"{session.status.value} → {status.value}"
            )
            return

        session.status = status

        if self._redis:
            await self._redis.hset(self._key(session_id), "status", status.value)

        logger.info(f"会话状态更新 | session_id={session_id} status={status.value}")

    async def save_messages(self, session_id: str, messages: list[Any]) -> None:
        """保存对话消息历史到 Redis

        Args:
            session_id: 会话 ID
            messages: pydantic_ai 消息列表
        """
        if not self._redis:
            return

        try:
            from pydantic_ai.messages import ModelMessagesTypeAdapter
            from src_deepagent.config.settings import get_settings

            settings = get_settings()
            max_turns = settings.memory.conversation_max_turns
            ttl = settings.memory.conversation_ttl

            # 裁剪：每轮 = 1 request + 1 response，保留最近 max_turns 轮
            max_messages = max_turns * 2
            if len(messages) > max_messages:
                messages = messages[-max_messages:]

            data = ModelMessagesTypeAdapter.dump_json(messages).decode()
            key = self._messages_key(session_id)
            await self._redis.set(key, data, ex=ttl)

            logger.info(f"对话历史保存 | session_id={session_id} messages={len(messages)}")
        except Exception as e:
            logger.warning(f"对话历史保存失败 | session_id={session_id} error={e}")

    async def load_messages(self, session_id: str) -> list[Any]:
        """从 Redis 加载对话消息历史

        Args:
            session_id: 会话 ID

        Returns:
            pydantic_ai 消息列表，失败返回空列表
        """
        if not self._redis:
            return []

        try:
            from pydantic_ai.messages import ModelMessagesTypeAdapter

            key = self._messages_key(session_id)
            data = await self._redis.get(key)
            if not data:
                return []

            messages = ModelMessagesTypeAdapter.validate_json(data)
            logger.info(f"对话历史加载 | session_id={session_id} messages={len(messages)}")
            return list(messages)
        except Exception as e:
            logger.warning(f"对话历史加载失败 | session_id={session_id} error={e}")
            return []
