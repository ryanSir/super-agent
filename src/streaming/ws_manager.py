"""WebSocket 连接管理

FastAPI 原生 WebSocket 管理，A2UI 双向通信。
"""

# 标准库
from typing import Dict, List, Optional

# 第三方库
from fastapi import WebSocket

# 本地模块
from src.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """WebSocket 连接池管理器

    管理活跃的 WebSocket 连接，支持按 session_id 推送 A2UI 事件。
    """

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """注册连接"""
        await websocket.accept()
        self._connections[session_id] = websocket
        logger.info(f"[WSManager] 连接注册 | session_id={session_id}")

    def disconnect(self, session_id: str) -> None:
        """注销连接"""
        self._connections.pop(session_id, None)
        logger.info(f"[WSManager] 连接注销 | session_id={session_id}")

    async def send_event(self, session_id: str, event: dict) -> bool:
        """向指定会话推送事件

        Args:
            session_id: 会话 ID
            event: A2UI 事件帧

        Returns:
            是否推送成功
        """
        ws = self._connections.get(session_id)
        if not ws:
            return False

        try:
            await ws.send_json(event)
            return True
        except Exception as e:
            logger.warning(f"[WSManager] 推送失败 | session_id={session_id} error={e}")
            self.disconnect(session_id)
            return False

    async def broadcast(self, event: dict) -> int:
        """广播事件到所有连接

        Returns:
            成功推送的连接数
        """
        success_count = 0
        dead_sessions = []

        for session_id, ws in self._connections.items():
            try:
                await ws.send_json(event)
                success_count += 1
            except Exception:
                dead_sessions.append(session_id)

        for sid in dead_sessions:
            self.disconnect(sid)

        return success_count

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @property
    def active_sessions(self) -> List[str]:
        return list(self._connections.keys())


# 全局单例
ws_manager = WebSocketManager()
