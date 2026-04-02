"""WebSocket 端点（A2UI 通信）

双向通信：接收用户消息，推送 A2UI 渲染指令。
"""

# 标准库
import json
import uuid
from typing import Dict

# 第三方库
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 本地模块
from src.core.logging import get_logger
from src.monitoring.trace_context import set_trace_context
from src.schemas.api import QueryRequest

logger = get_logger(__name__)

router = APIRouter()

# 活跃 WebSocket 连接池
_active_connections: Dict[str, WebSocket] = {}


@router.websocket("/agent/{session_id}")
async def agent_websocket(websocket: WebSocket, session_id: str) -> None:
    """Agent WebSocket 端点

    支持双向通信：
    - 客户端 → 服务端：发送查询请求
    - 服务端 → 客户端：推送 A2UI 渲染指令、进度更新、文本流

    Args:
        websocket: WebSocket 连接
        session_id: 会话 ID
    """
    await websocket.accept()
    _active_connections[session_id] = websocket

    trace_id = set_trace_context(session_id=session_id)

    logger.info(
        f"[WebSocket] 连接建立 | session_id={session_id} trace_id={trace_id}"
    )

    # 发送连接确认
    await websocket.send_json({
        "event_type": "connected",
        "session_id": session_id,
        "trace_id": trace_id,
    })

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.info(
                f"[WebSocket] 收到消息 | "
                f"session_id={session_id} type={message.get('type', 'unknown')}"
            )

            msg_type = message.get("type", "")

            if msg_type == "query":
                # 处理查询请求
                await _handle_query(websocket, session_id, trace_id, message)
            elif msg_type == "ping":
                await websocket.send_json({"event_type": "pong"})
            else:
                await websocket.send_json({
                    "event_type": "error",
                    "message": f"未知消息类型: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] 连接断开 | session_id={session_id}")
    except json.JSONDecodeError as e:
        logger.warning(f"[WebSocket] JSON 解析失败 | session_id={session_id} error={e}")
    except Exception as e:
        logger.error(
            f"[WebSocket] 异常 | session_id={session_id} error={e}",
            exc_info=True,
        )
    finally:
        _active_connections.pop(session_id, None)


async def push_to_session(session_id: str, event: dict) -> bool:
    """向指定会话推送 A2UI 事件

    先持久化到 Redis Stream，再尝试通过 WebSocket 推送。
    即使 WebSocket 断开，事件仍会写入 Stream，支持断点续传。

    Args:
        session_id: 会话 ID
        event: A2UI 事件帧

    Returns:
        是否通过 WebSocket 推送成功
    """
    # 1. 持久化到 Redis Stream（无论 WS 是否在线）
    try:
        from src.streaming.stream_adapter import publish_event
        event_id = await publish_event(session_id, event)
        if event_id:
            event["_event_id"] = event_id
    except Exception as e:
        logger.warning(f"[WebSocket] Redis 持久化失败 | session_id={session_id} error={e}")

    # 2. 尝试通过 WebSocket 推送
    ws = _active_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(event)
            return True
        except Exception as e:
            logger.warning(
                f"[WebSocket] 推送失败 | session_id={session_id} error={e}"
            )
            _active_connections.pop(session_id, None)
    return False


def get_active_sessions() -> list[str]:
    """获取所有活跃 WebSocket 会话 ID"""
    return list(_active_connections.keys())


# ============================================================
# 内部函数
# ============================================================

async def _handle_query(
    websocket: WebSocket,
    session_id: str,
    trace_id: str,
    message: dict,
) -> None:
    """处理 WebSocket 查询请求"""
    query = message.get("query", "")
    if not query:
        await websocket.send_json({
            "event_type": "error",
            "message": "query 不能为空",
        })
        return

    # 通知前端：开始处理
    await websocket.send_json({
        "event_type": "session_created",
        "session_id": session_id,
        "trace_id": trace_id,
    })

    # 异步启动编排
    import asyncio
    asyncio.create_task(
        _run_ws_orchestration(session_id, trace_id, query, websocket)
    )


async def _run_ws_orchestration(
    session_id: str,
    trace_id: str,
    query: str,
    websocket: WebSocket,
) -> None:
    """WebSocket 编排流程"""
    from src.orchestrator.orchestrator_agent import run_orchestrator

    try:
        # 推送规划中状态
        await push_to_session(session_id, {
            "event_type": "process_update",
            "phase": "thinking",
            "status": "in_progress",
            "message": "正在理解你的请求...",
        })

        accumulated_answer = []
        async for token in run_orchestrator(
            query=query,
            session_id=session_id,
        ):
            if not token:
                continue
            accumulated_answer.append(token)
            await push_to_session(session_id, {
                "event_type": "text_stream",
                "delta": token,
                "is_final": False,
            })

        await push_to_session(session_id, {
            "event_type": "text_stream",
            "delta": "",
            "is_final": True,
        })

        # 推送完成信号
        await push_to_session(session_id, {
            "event_type": "session_completed",
            "session_id": session_id,
            "trace_id": trace_id,
        })

    except Exception as e:
        logger.error(
            f"[WebSocket] 编排异常 | session_id={session_id} error_type={type(e).__name__} error={e}",
            exc_info=True,
        )
        await push_to_session(session_id, {
            "event_type": "session_failed",
            "session_id": session_id,
            "error": f"{type(e).__name__}: {str(e)[:500]}",
        })
    except BaseException as e:
        logger.error(
            f"[WebSocket] 编排严重异常 | session_id={session_id} error_type={type(e).__name__} error={e}",
            exc_info=True,
        )
        await push_to_session(session_id, {
            "event_type": "session_failed",
            "session_id": session_id,
            "error": f"{type(e).__name__}: {str(e)[:500]}",
        })
