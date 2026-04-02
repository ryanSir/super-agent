"""测试 ToolErrorHandlingMiddleware"""

import pytest

from src.middleware.context import MiddlewareContext
from src.middleware.tool_error_handling import ToolErrorHandlingMiddleware


def _make_context() -> MiddlewareContext:
    return MiddlewareContext(session_id="test-sess", trace_id="test-trace")


@pytest.mark.asyncio
async def test_captures_exception_returns_message():
    """捕获异常并返回格式化错误消息"""
    mw = ToolErrorHandlingMiddleware()
    ctx = _make_context()

    result = await mw.on_tool_error(ctx, "my_tool", RuntimeError("something broke"))

    assert result is not None
    assert "my_tool" in result
    assert "RuntimeError" in result
    assert "something broke" in result


@pytest.mark.asyncio
async def test_truncates_long_error():
    """超过 500 字符的错误消息被截断"""
    mw = ToolErrorHandlingMiddleware()
    ctx = _make_context()

    long_msg = "x" * 1000
    result = await mw.on_tool_error(ctx, "tool", RuntimeError(long_msg))

    # 错误详情部分应被截断
    assert "..." in result


@pytest.mark.asyncio
async def test_empty_error_message():
    """空错误消息使用类名"""
    mw = ToolErrorHandlingMiddleware()
    ctx = _make_context()

    result = await mw.on_tool_error(ctx, "tool", RuntimeError(""))

    assert "RuntimeError" in result


@pytest.mark.asyncio
async def test_returns_continue_instruction():
    """错误消息包含继续执行的指引"""
    mw = ToolErrorHandlingMiddleware()
    ctx = _make_context()

    result = await mw.on_tool_error(ctx, "tool", ValueError("bad input"))

    assert "Continue with available context" in result
