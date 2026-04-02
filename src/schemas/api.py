"""API 请求/响应模型

定义 REST API 和 SSE 事件的结构化契约。
"""

# 标准库
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

# 第三方库
from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================

class QueryRequest(BaseModel):
    """用户查询请求

    Args:
        query: 用户输入的自然语言查询
        session_id: 会话 ID（可选，不传则新建会话）
        mode: 执行模式
        context: 附加上下文（如选中的文档、过滤条件等）
    """
    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    mode: str = Field(default="auto", pattern="^(auto|plan_and_execute|direct)$")
    context: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# 响应模型
# ============================================================

class QueryResponse(BaseModel):
    """查询响应"""
    success: bool = True
    session_id: str
    trace_id: str
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: Dict[str, Any]


# ============================================================
# SSE 事件模型
# ============================================================

class EventType(str, enum.Enum):
    """SSE 事件类型"""
    # 生命周期
    SESSION_CREATED = "session_created"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"

    # 规划阶段
    PLANNING_STARTED = "planning_started"
    PLANNING_COMPLETED = "planning_completed"

    # 执行阶段
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # 流式输出
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

    # A2UI 渲染
    RENDER_WIDGET = "render_widget"

    # 记忆系统
    MEMORY_UPDATE = "memory_update"

    # Middleware 事件
    MIDDLEWARE_EVENT = "middleware_event"

    # 心跳
    HEARTBEAT = "heartbeat"


class StreamEvent(BaseModel):
    """SSE 事件帧

    Args:
        event_type: 事件类型
        trace_id: 全链路追踪 ID
        session_id: 会话 ID
        data: 事件数据
        timestamp: 事件时间戳
    """
    event_type: EventType
    trace_id: str = ""
    session_id: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
