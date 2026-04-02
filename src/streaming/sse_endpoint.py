"""SSE 端点

基于 sse-starlette 的 SSE 端点封装，支持 Last-Event-ID 断点续传。
"""

# 标准库
import json
from datetime import datetime

# 第三方库
from sse_starlette.sse import EventSourceResponse

# 本地模块
from src.core.logging import get_logger
from src.streaming.stream_adapter import get_session_events

logger = get_logger(__name__)


def create_sse_response(
    session_id: str,
    last_event_id: str = "0-0",
) -> EventSourceResponse:
    """创建 SSE 响应，支持断点续传

    Args:
        session_id: 会话 ID
        last_event_id: 上次收到的事件 ID（来自 Last-Event-ID 请求头）

    Returns:
        EventSourceResponse: SSE 流式响应
    """

    async def event_generator():
        async for event in get_session_events(session_id, last_event_id=last_event_id):
            yield {
                "event": "message",
                "id": event.get("_event_id", ""),
                "data": _serialize(event),
            }

    return EventSourceResponse(event_generator())


def _serialize(event: dict) -> str:
    """序列化事件为 JSON"""

    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    return json.dumps(event, default=default, ensure_ascii=False)
