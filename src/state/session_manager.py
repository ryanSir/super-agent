"""会话状态机（Redis 持久化）

管理会话生命周期：CREATED → PLANNING → EXECUTING → COMPLETED/FAILED
会话元数据持久化到 Redis Hash，支持跨进程恢复。
"""

# 标准库
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# 本地模块
from src.core.logging import get_logger
from src.schemas.agent import SessionStatus

logger = get_logger(__name__)

# Redis key 模板与常量
SESSION_META_KEY = "session:meta:{session_id}"
SESSION_TTL = 3600  # 1 小时


class Session:
    """会话实例"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.status = SessionStatus.CREATED
        self.trace_id = ""
        self.query = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None

    def transition(self, new_status: SessionStatus) -> None:
        """状态转换"""
        valid_transitions = {
            SessionStatus.CREATED: {SessionStatus.PLANNING, SessionStatus.FAILED},
            SessionStatus.PLANNING: {SessionStatus.EXECUTING, SessionStatus.FAILED},
            SessionStatus.EXECUTING: {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.TIMEOUT},
            SessionStatus.COMPLETED: set(),
            SessionStatus.FAILED: set(),
            SessionStatus.TIMEOUT: set(),
        }

        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            logger.warning(
                f"[Session] 非法状态转换 | "
                f"session_id={self.session_id} {self.status} → {new_status}"
            )
            return

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()

        logger.info(
            f"[Session] 状态转换 | "
            f"session_id={self.session_id} {old_status} → {new_status}"
        )


class SessionManager:
    """Redis 持久化会话管理器

    本地 dict 作为热缓存，Redis Hash 作为持久化存储。
    """

    def __init__(self) -> None:
        self._local_cache: Dict[str, Session] = {}

    async def create_session(
        self,
        session_id: Optional[str] = None,
        trace_id: str = "",
        query: str = "",
    ) -> Session:
        """创建新会话"""
        sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        session = Session(sid)
        session.trace_id = trace_id
        session.query = query

        self._local_cache[sid] = session

        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            key = SESSION_META_KEY.format(session_id=sid)
            await r.hset(key, mapping={
                "session_id": sid,
                "status": session.status.value,
                "trace_id": trace_id,
                "query": query,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "error": "",
            })
            await r.expire(key, SESSION_TTL)
        except Exception as e:
            logger.warning(f"[SessionManager] Redis 写入失败 | session_id={sid} error={e}")

        logger.info(f"[SessionManager] 创建会话 | session_id={sid}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话（优先本地缓存，回退 Redis）"""
        if session_id in self._local_cache:
            return self._local_cache[session_id]

        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            key = SESSION_META_KEY.format(session_id=session_id)
            data = await r.hgetall(key)
            if not data:
                return None

            session = Session(session_id)
            session.status = SessionStatus(data.get("status", "created"))
            session.trace_id = data.get("trace_id", "")
            session.query = data.get("query", "")
            session.created_at = datetime.fromisoformat(data["created_at"])
            session.updated_at = datetime.fromisoformat(data["updated_at"])
            session.error = data.get("error") or None

            self._local_cache[session_id] = session
            return session
        except Exception as e:
            logger.warning(f"[SessionManager] Redis 读取失败 | session_id={session_id} error={e}")
            return None

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """更新会话状态"""
        session = await self.get_session(session_id)
        if not session:
            return

        session.transition(status)

        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            key = SESSION_META_KEY.format(session_id=session_id)
            await r.hset(key, mapping={
                "status": status.value,
                "updated_at": datetime.now().isoformat(),
            })
            await r.expire(key, SESSION_TTL)
        except Exception as e:
            logger.warning(f"[SessionManager] Redis 更新失败 | session_id={session_id} error={e}")

    async def remove_session(self, session_id: str) -> None:
        """移除会话"""
        self._local_cache.pop(session_id, None)
        try:
            from src.core.dependencies import get_redis_client
            r = await get_redis_client()
            await r.delete(SESSION_META_KEY.format(session_id=session_id))
        except Exception as e:
            logger.warning(f"[SessionManager] Redis 删除失败 | session_id={session_id} error={e}")

    @property
    def active_count(self) -> int:
        return len(self._local_cache)

    def list_sessions(self) -> list[Dict[str, Any]]:
        """列出本地缓存中的会话"""
        return [
            {
                "session_id": s.session_id,
                "status": s.status.value,
                "query": s.query[:50],
                "created_at": s.created_at.isoformat(),
            }
            for s in self._local_cache.values()
        ]


# 全局单例
session_manager = SessionManager()
