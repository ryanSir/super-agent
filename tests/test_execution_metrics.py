"""测试 MetricsCollector"""

import time

import pytest

from src.monitoring.execution_metrics import MetricsCollector, StepStats
from src.monitoring.pipeline_events import EventStatus, PipelineEvent


def _make_event(
    step: str = "worker.native.rag",
    status: EventStatus = EventStatus.completed,
    duration_ms: float = 100.0,
    trace_id: str = "trace-001",
    timestamp: float = None,
    metadata: dict = None,
) -> PipelineEvent:
    return PipelineEvent(
        trace_id=trace_id,
        request_id="req-001",
        session_id="sess-001",
        step=step,
        status=status,
        timestamp=timestamp or time.time(),
        duration_ms=duration_ms,
        metadata=metadata or {},
    )


class TestMetricsCollectorRecord:
    """record 方法测试"""

    def test_record_event(self):
        collector = MetricsCollector(maxlen=100)
        event = _make_event()
        collector.record(event)
        assert len(collector._events) == 1

    def test_buffer_overflow_auto_evict(self):
        """缓冲区满时自动淘汰最旧事件"""
        collector = MetricsCollector(maxlen=5)
        for i in range(10):
            collector.record(_make_event(trace_id=f"trace-{i}"))
        assert len(collector._events) == 5
        # 最旧的 5 个被淘汰
        assert collector._events[0].trace_id == "trace-5"

    def test_record_exception_does_not_raise(self):
        """record 异常不中断"""
        collector = MetricsCollector(maxlen=100)
        # 传入非 PipelineEvent 不应抛异常（deque.append 接受任何对象）
        collector.record("not an event")  # type: ignore
        assert len(collector._events) == 1


class TestGetStepStats:
    """get_step_stats 方法测试"""

    def test_basic_stats(self):
        collector = MetricsCollector(maxlen=100)
        for d in [100.0, 200.0, 300.0, 400.0, 500.0]:
            collector.record(_make_event(duration_ms=d))

        stats = collector.get_step_stats("worker.native.rag", window_minutes=5)
        assert stats.count == 5
        assert stats.avg_ms == 300.0
        assert stats.max_ms == 500.0
        assert stats.error_count == 0
        assert stats.error_rate == 0.0

    def test_stats_with_errors(self):
        collector = MetricsCollector(maxlen=100)
        collector.record(_make_event(duration_ms=100.0))
        collector.record(_make_event(duration_ms=200.0))
        collector.record(_make_event(
            status=EventStatus.failed, duration_ms=50.0,
            metadata={"error_type": "ValueError"},
        ))

        stats = collector.get_step_stats("worker.native.rag", window_minutes=5)
        assert stats.count == 3
        assert stats.error_count == 1
        assert abs(stats.error_rate - 1 / 3) < 0.01

    def test_no_data_returns_zero_stats(self):
        collector = MetricsCollector(maxlen=100)
        stats = collector.get_step_stats("nonexistent.step", window_minutes=5)
        assert stats.count == 0
        assert stats.avg_ms == 0.0
        assert stats.error_rate == 0.0

    def test_window_filter(self):
        """超出时间窗口的事件不计入"""
        collector = MetricsCollector(maxlen=100)
        old_time = time.time() - 600  # 10 分钟前
        collector.record(_make_event(duration_ms=999.0, timestamp=old_time))
        collector.record(_make_event(duration_ms=100.0))

        stats = collector.get_step_stats("worker.native.rag", window_minutes=5)
        assert stats.count == 1
        assert stats.avg_ms == 100.0

    def test_started_events_excluded(self):
        """started 事件不计入统计"""
        collector = MetricsCollector(maxlen=100)
        collector.record(_make_event(status=EventStatus.started, duration_ms=None))
        collector.record(_make_event(duration_ms=100.0))

        stats = collector.get_step_stats("worker.native.rag", window_minutes=5)
        assert stats.count == 1


class TestGetTraceTimeline:
    """get_trace_timeline 方法测试"""

    def test_returns_events_sorted_by_timestamp(self):
        collector = MetricsCollector(maxlen=100)
        now = time.time()
        collector.record(_make_event(trace_id="t1", timestamp=now + 2, step="gateway.respond"))
        collector.record(_make_event(trace_id="t1", timestamp=now, step="gateway.receive"))
        collector.record(_make_event(trace_id="t1", timestamp=now + 1, step="intent.classify"))
        collector.record(_make_event(trace_id="t2", timestamp=now))  # 不同 trace

        timeline = collector.get_trace_timeline("t1")
        assert len(timeline) == 3
        assert timeline[0].step == "gateway.receive"
        assert timeline[1].step == "intent.classify"
        assert timeline[2].step == "gateway.respond"

    def test_nonexistent_trace_returns_empty(self):
        collector = MetricsCollector(maxlen=100)
        assert collector.get_trace_timeline("nonexistent") == []


class TestGetOverview:
    """get_overview 方法测试"""

    def test_overview_sorted_by_avg_ms_desc(self):
        collector = MetricsCollector(maxlen=100)
        # 快步骤
        collector.record(_make_event(step="intent.classify", duration_ms=10.0))
        # 慢步骤
        collector.record(_make_event(step="worker.native.rag", duration_ms=500.0))
        # 中等步骤
        collector.record(_make_event(step="orchestrator.plan", duration_ms=200.0))

        overview = collector.get_overview(window_minutes=5)
        assert len(overview) == 3
        assert overview[0].avg_ms == 500.0  # rag 最慢
        assert overview[2].avg_ms == 10.0   # classify 最快

    def test_empty_overview(self):
        collector = MetricsCollector(maxlen=100)
        assert collector.get_overview(window_minutes=5) == []
