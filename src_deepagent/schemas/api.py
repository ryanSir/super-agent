"""API 数据模型

定义 REST/WebSocket 请求响应和事件类型。
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


# ── 事件类型 ──────────────────────────────────────────────


class EventType(str, enum.Enum):
    """SSE 事件类型"""

    SESSION_CREATED = "session_created"
    THINKING = "thinking"
    STEP = "step"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TEXT_STREAM = "text_stream"
    RENDER_WIDGET = "render_widget"
    MIDDLEWARE_EVENT = "middleware_event"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    HEARTBEAT = "heartbeat"

    # Sub-Agent 生命周期事件
    SUB_AGENT_STARTED = "sub_agent_started"
    SUB_AGENT_PROGRESS = "sub_agent_progress"
    SUB_AGENT_COMPLETED = "sub_agent_completed"


# ── 请求 / 响应 ──────────────────────────────────────────


class QueryRequest(BaseModel):
    """用户查询请求"""

    query: str = Field(description="用户自然语言请求")
    session_id: str | None = Field(default=None, description="会话 ID（可选，自动生成）")
    mode: str = Field(
        default="auto",
        pattern=r"^(auto|direct|plan_and_execute|sub_agent)$",
        description="执行模式",
    )
    context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")
    user_id: str = Field(default="default", description="用户 ID")


class QueryResponse(BaseModel):
    """查询响应"""

    success: bool = Field(default=True)
    session_id: str = Field(description="会话 ID")
    trace_id: str = Field(description="追踪 ID")
    message: str = Field(default="")
    data: dict[str, Any] | None = Field(default=None)


class StreamEvent(BaseModel):
    """SSE 事件"""

    event_type: EventType = Field(description="事件类型")
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据")
    session_id: str = Field(default="", description="会话 ID")
    timestamp: float = Field(default=0.0, description="时间戳")
