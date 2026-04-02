"""测试 MiddlewarePipeline 洋葱模型执行顺序、异常传播、配置开关"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.middleware.base import AgentMiddleware
from src.middleware.context import MiddlewareContext, TokenUsage
from src.middleware.pipeline import MiddlewarePipeline
from src.schemas.agent import OrchestratorOutput


class RecordingMiddleware(AgentMiddleware):
    """记录调用顺序的测试 middleware"""

    def __init__(self, name: str, log: list):
        self.name = name
        self.log = log

    async def before_agent(self, context):
        self.log.append(f"{self.name}.before")

    async def after_agent(self, context, result):
        self.log.append(f"{self.name}.after")
        return result


class FailingBeforeMiddleware(AgentMiddleware):
    async def before_agent(self, context):
        raise RuntimeError("before_agent failed")


class FailingAfterMiddleware(AgentMiddleware):
    async def after_agent(self, context, result):
        raise RuntimeError("after_agent failed")


def _make_context() -> MiddlewareContext:
    return MiddlewareContext(session_id="test-sess", trace_id="test-trace")


def _make_output() -> OrchestratorOutput:
    return OrchestratorOutput(answer="test answer", worker_results=[])


@pytest.mark.asyncio
async def test_onion_execution_order():
    """before 正序、after 逆序（洋葱模型）"""
    log = []
    mw_a = RecordingMiddleware("A", log)
    mw_b = RecordingMiddleware("B", log)
    mw_c = RecordingMiddleware("C", log)

    pipeline = MiddlewarePipeline([mw_a, mw_b, mw_c])

    output = _make_output()

    async def agent_fn(ctx):
        log.append("agent")
        return output

    await pipeline.execute(_make_context(), agent_fn)

    assert log == [
        "A.before", "B.before", "C.before",
        "agent",
        "C.after", "B.after", "A.after",
    ]


@pytest.mark.asyncio
async def test_before_agent_exception_stops_pipeline():
    """before_agent 抛异常时，不执行 agent 和后续 middleware"""
    log = []
    mw_a = RecordingMiddleware("A", log)
    mw_fail = FailingBeforeMiddleware()
    mw_c = RecordingMiddleware("C", log)

    pipeline = MiddlewarePipeline([mw_a, mw_fail, mw_c])

    async def agent_fn(ctx):
        log.append("agent")
        return _make_output()

    with pytest.raises(RuntimeError, match="before_agent failed"):
        await pipeline.execute(_make_context(), agent_fn)

    assert "agent" not in log
    assert "C.before" not in log


@pytest.mark.asyncio
async def test_after_agent_exception_propagates():
    """after_agent 抛异常时，异常传播给调用方"""
    pipeline = MiddlewarePipeline([FailingAfterMiddleware()])

    async def agent_fn(ctx):
        return _make_output()

    with pytest.raises(RuntimeError, match="after_agent failed"):
        await pipeline.execute(_make_context(), agent_fn)


@pytest.mark.asyncio
async def test_empty_pipeline():
    """空 pipeline 直接执行 agent"""
    pipeline = MiddlewarePipeline([])
    output = _make_output()

    async def agent_fn(ctx):
        return output

    result = await pipeline.execute(_make_context(), agent_fn)
    assert result.answer == "test answer"


@pytest.mark.asyncio
async def test_middleware_shares_context():
    """middleware 间通过 context.metadata 共享状态"""

    class WriterMiddleware(AgentMiddleware):
        async def before_agent(self, context):
            context.metadata["key"] = "value"

    class ReaderMiddleware(AgentMiddleware):
        def __init__(self):
            self.read_value = None

        async def after_agent(self, context, result):
            self.read_value = context.metadata.get("key")
            return result

    reader = ReaderMiddleware()
    pipeline = MiddlewarePipeline([WriterMiddleware(), reader])

    async def agent_fn(ctx):
        return _make_output()

    await pipeline.execute(_make_context(), agent_fn)
    assert reader.read_value == "value"


def test_non_async_hook_raises_type_error():
    """非 async 钩子方法在子类定义时抛出 TypeError"""
    with pytest.raises(TypeError, match="必须是 async 方法"):
        class BadMiddleware(AgentMiddleware):
            def before_agent(self, context):
                pass
