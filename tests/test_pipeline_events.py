"""测试 PipelineEvent 模型、pipeline_step 上下文管理器、log_pipeline_step 装饰器"""

import asyncio
import time

import pytest

from src.monitoring.pipeline_events import (
    EventStatus,
    PipelineEvent,
    StepStats,
    log_pipeline_step,
    pipeline_step,
    pipeline_step_sync,
)


class TestPipelineEvent:
    """PipelineEvent 数据模型测试"""

    def test_create_event(self):
        event = PipelineEvent(
            trace_id="trace-001",
            request_id="req-001",
            session_id="sess-001",
            step="worker.native.rag",
            status=EventStatus.started,
            timestamp=time.time(),
        )
        assert event.step == "worker.native.rag"
        assert event.status == EventStatus.started
        assert event.duration_ms is None
        assert event.metadata == {}

    def test_add_metadata(self):
        event = PipelineEvent(
            trace_id="t", request_id="r", session_id="s",
            step="intent.classify", status=EventStatus.completed,
            timestamp=time.time(), duration_ms=42.0,
        )
        event.add_metadata(worker_type="rag", count=5)
        assert event.metadata["worker_type"] == "rag"
        assert event.metadata["count"] == 5

    def test_to_log_string_started(self):
        event = PipelineEvent(
            trace_id="t", request_id="r", session_id="s",
            step="gateway.receive", status=EventStatus.started,
            timestamp=time.time(),
        )
        log = event.to_log_string()
        assert "PIPELINE_EVENT |" in log
        assert "step=gateway.receive" in log
        assert "status=started" in log
        assert "duration_ms" not in log

    def test_to_log_string_completed_with_metadata(self):
        event = PipelineEvent(
            trace_id="t", request_id="r", session_id="s",
            step="worker.native.rag", status=EventStatus.completed,
            timestamp=time.time(), duration_ms=123.4,
            metadata={"worker_type": "rag"},
        )
        log = event.to_log_string()
        assert "duration_ms=123.4" in log
        assert "worker_type=rag" in log

    def test_to_log_string_failed(self):
        event = PipelineEvent(
            trace_id="t", request_id="r", session_id="s",
            step="orchestrator.plan", status=EventStatus.failed,
            timestamp=time.time(), duration_ms=50.0,
            metadata={"error_type": "ValueError", "error_msg": "bad input"},
        )
        log = event.to_log_string()
        assert "status=failed" in log
        assert "error_type=ValueError" in log


class TestPipelineStep:
    """pipeline_step 上下文管理器测试"""

    @pytest.mark.asyncio
    async def test_successful_step(self):
        async with pipeline_step("intent.classify") as event:
            await asyncio.sleep(0.01)
            event.add_metadata(mode="auto")

        assert event.status == EventStatus.completed
        assert event.duration_ms is not None
        assert event.duration_ms >= 10
        assert event.metadata["mode"] == "auto"

    @pytest.mark.asyncio
    async def test_failed_step(self):
        with pytest.raises(ValueError, match="test error"):
            async with pipeline_step("orchestrator.plan") as event:
                raise ValueError("test error")

        assert event.status == EventStatus.failed
        assert event.duration_ms is not None
        assert event.metadata["error_type"] == "ValueError"
        assert "test error" in event.metadata["error_msg"]

    @pytest.mark.asyncio
    async def test_step_with_initial_metadata(self):
        async with pipeline_step("worker.native.rag", metadata={"task_id": "t1"}) as event:
            pass

        assert event.metadata["task_id"] == "t1"

    @pytest.mark.asyncio
    async def test_event_recording_failure_does_not_break_business(self):
        """事件记录自身异常不影响业务"""
        result = None
        async with pipeline_step("gateway.receive") as event:
            result = 42

        assert result == 42


class TestPipelineStepSync:
    """pipeline_step_sync 同步上下文管理器测试"""

    def test_successful_sync_step(self):
        with pipeline_step_sync("intent.classify") as event:
            time.sleep(0.01)

        assert event.status == EventStatus.completed
        assert event.duration_ms >= 10

    def test_failed_sync_step(self):
        with pytest.raises(RuntimeError):
            with pipeline_step_sync("orchestrator.plan") as event:
                raise RuntimeError("sync error")

        assert event.status == EventStatus.failed


class TestLogPipelineStepDecorator:
    """log_pipeline_step 装饰器测试"""

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        @log_pipeline_step("intent.classify")
        async def classify(query: str) -> str:
            return f"classified: {query}"

        result = await classify("hello")
        assert result == "classified: hello"

    def test_sync_decorator(self):
        @log_pipeline_step("toolset.assemble")
        def assemble(mode: str) -> str:
            return f"assembled: {mode}"

        result = assemble("auto")
        assert result == "assembled: auto"

    @pytest.mark.asyncio
    async def test_async_decorator_propagates_exception(self):
        @log_pipeline_step("orchestrator.execute")
        async def failing_fn():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing_fn()

    def test_sync_decorator_propagates_exception(self):
        @log_pipeline_step("middleware.before")
        def failing_fn():
            raise RuntimeError("sync boom")

        with pytest.raises(RuntimeError, match="sync boom"):
            failing_fn()
