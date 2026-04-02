"""Trace ID 上下文传播

基于 contextvars 实现跨 Worker/沙箱的 Trace ID 透传。
"""

# 标准库
import uuid
from contextvars import ContextVar
from typing import Optional

# Trace 上下文变量
current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")
current_session_id: ContextVar[str] = ContextVar("current_session_id", default="")
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")


def generate_trace_id() -> str:
    """生成唯一 Trace ID"""
    return f"trace-{uuid.uuid4().hex[:12]}"


def set_trace_context(
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """设置当前请求的 Trace 上下文

    Args:
        trace_id: Trace ID，不传则自动生成
        session_id: 会话 ID
        user_id: 用户 ID

    Returns:
        实际使用的 trace_id
    """
    tid = trace_id or generate_trace_id()
    current_trace_id.set(tid)
    if session_id:
        current_session_id.set(session_id)
    if user_id:
        current_user_id.set(user_id)
    return tid


def get_trace_id() -> str:
    """获取当前 Trace ID"""
    return current_trace_id.get("")


def get_session_id() -> str:
    """获取当前 Session ID"""
    return current_session_id.get("")
