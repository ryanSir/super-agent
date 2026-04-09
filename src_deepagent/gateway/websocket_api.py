"""WebSocket 双向通信端点"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket 双向通信

    客户端可发送控制消息（如取消任务），服务端推送实时事件。
    """
    await websocket.accept()
    logger.info(f"WebSocket 连接 | session_id={session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "cancel":
                    logger.info(f"WebSocket 取消请求 | session_id={session_id}")
                    await websocket.send_json({
                        "type": "cancelled",
                        "session_id": session_id,
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知消息类型: {msg_type}",
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "无效的 JSON 格式",
                })
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开 | session_id={session_id}")
