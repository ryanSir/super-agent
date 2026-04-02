"""测试 LoopDetectionMiddleware"""

import pytest
from unittest.mock import AsyncMock, patch

from src.middleware.context import MiddlewareContext, TokenUsage
from src.middleware.loop_detection import LoopDetectionMiddleware, _hash_tool_calls
from src.schemas.agent import OrchestratorOutput


def _make_context(messages=None) -> MiddlewareContext:
    return MiddlewareContext(
        session_id="test-sess",
        trace_id="test-trace",
        messages=messages or [],
    )


def _make_output(answer="test") -> OrchestratorOutput:
    return OrchestratorOutput(answer=answer, worker_results=[])


def _make_tool_message(tool_name: str, args: dict):
    """模拟 PydanticAI 的 tool call 消息"""
    class FakePart:
        def __init__(self, name, a):
            self.tool_name = name
            self.args = a
            self.content = "result"

    class FakeMsg:
        def __init__(self, parts_list):
            self.parts = parts_list

    return FakeMsg([FakePart(tool_name, args)])


class TestHashToolCalls:
    def test_same_calls_same_hash(self):
        calls = [{"name": "foo", "args": {"x": 1}}]
        assert _hash_tool_calls(calls) == _hash_tool_calls(calls)

    def test_different_args_different_hash(self):
        a = [{"name": "foo", "args": {"x": 1}}]
        b = [{"name": "foo", "args": {"x": 2}}]
        assert _hash_tool_calls(a) != _hash_tool_calls(b)

    def test_order_independent(self):
        a = [{"name": "foo", "args": {}}, {"name": "bar", "args": {}}]
        b = [{"name": "bar", "args": {}}, {"name": "foo", "args": {}}]
        assert _hash_tool_calls(a) == _hash_tool_calls(b)


@pytest.mark.asyncio
@patch("src.middleware.loop_detection.LoopDetectionMiddleware._publish_event", new_callable=AsyncMock)
async def test_no_trigger_below_threshold(mock_pub):
    """低于 warn_threshold 不触发"""
    mw = LoopDetectionMiddleware(warn_threshold=3, hard_limit=5)
    msg = _make_tool_message("foo", {"x": 1})

    for _ in range(2):
        ctx = _make_context([msg])
        result = await mw.after_agent(ctx, _make_output())
        assert "LOOP DETECTED" not in (result.answer or "")

    mock_pub.assert_not_called()


@pytest.mark.asyncio
@patch("src.middleware.loop_detection.LoopDetectionMiddleware._publish_event", new_callable=AsyncMock)
async def test_warn_at_threshold(mock_pub):
    """达到 warn_threshold 注入警告"""
    mw = LoopDetectionMiddleware(warn_threshold=2, hard_limit=5)
    msg = _make_tool_message("foo", {"x": 1})

    for _ in range(2):
        ctx = _make_context([msg])
        await mw.after_agent(ctx, _make_output())

    # 第 2 次应该触发警告
    mock_pub.assert_called_once()
    call_args = mock_pub.call_args
    assert call_args[0][1] == "warning"


@pytest.mark.asyncio
@patch("src.middleware.loop_detection.LoopDetectionMiddleware._publish_event", new_callable=AsyncMock)
async def test_hard_stop_at_limit(mock_pub):
    """达到 hard_limit 强制终止"""
    mw = LoopDetectionMiddleware(warn_threshold=2, hard_limit=3)
    msg = _make_tool_message("foo", {"x": 1})

    result = None
    for _ in range(3):
        ctx = _make_context([msg])
        result = await mw.after_agent(ctx, _make_output())

    assert "FORCED STOP" in result.answer


@pytest.mark.asyncio
@patch("src.middleware.loop_detection.LoopDetectionMiddleware._publish_event", new_callable=AsyncMock)
async def test_different_args_no_trigger(mock_pub):
    """不同参数不触发循环检测"""
    mw = LoopDetectionMiddleware(warn_threshold=2, hard_limit=3)

    for i in range(5):
        msg = _make_tool_message("foo", {"x": i})
        ctx = _make_context([msg])
        result = await mw.after_agent(ctx, _make_output())
        assert "LOOP" not in (result.answer or "")


@pytest.mark.asyncio
async def test_reset_clears_state():
    """reset 清除追踪状态"""
    mw = LoopDetectionMiddleware(warn_threshold=2, hard_limit=5)
    msg = _make_tool_message("foo", {"x": 1})

    ctx = _make_context([msg])
    await mw.after_agent(ctx, _make_output())

    mw.reset("test-sess")
    assert "test-sess" not in mw._history
