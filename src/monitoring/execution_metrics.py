"""执行指标采集

内存环形缓冲存储 PipelineEvent，提供耗时统计和链路还原。
"""

# 标准库
import statistics
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional

# 本地模块
from src.core.logging import get_logger

logger = get_logger(__name__)

# 单例
_collector: Optional["MetricsCollector"] = None


@dataclass
class StepStats:
    """步骤耗时统计"""
    count: int = 0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    max_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0


class MetricsCollector:
    """执行指标采集器

    使用 deque 环形缓冲存储事件，协程安全（CPython GIL 保护 deque.append）。
    """

    def __init__(self, maxlen: int = 10000) -> None:
        self._events: deque = deque(maxlen=maxlen)

    def record(self, event: "PipelineEvent") -> None:
        """记录事件，异常不中断业务"""
        try:
            self._events.append(event)
        except Exception as e:
            logger.warning(f"[MetricsCollector] 记录失败 | error={e}")

    def get_step_stats(self, step: str, window_minutes: int = 5) -> StepStats:
        """查询指定步骤的耗时统计"""
        cutoff = time.time() - window_minutes * 60
        durations: List[float] = []
        error_count = 0
        total = 0

        for ev in self._events:
            if ev.step != step or ev.timestamp < cutoff:
                continue
            if ev.status.value == "started":
                continue
            total += 1
            if ev.status.value == "failed":
                error_count += 1
            if ev.duration_ms is not None:
                durations.append(ev.duration_ms)

        if not durations:
            return StepStats(
                count=total,
                error_count=error_count,
                error_rate=error_count / total if total else 0.0,
            )

        durations.sort()
        n = len(durations)
        return StepStats(
            count=total,
            avg_ms=statistics.mean(durations),
            p50_ms=durations[int(n * 0.5)] if n else 0.0,
            p95_ms=durations[min(int(n * 0.95), n - 1)] if n else 0.0,
            p99_ms=durations[min(int(n * 0.99), n - 1)] if n else 0.0,
            max_ms=max(durations),
            error_count=error_count,
            error_rate=error_count / total if total else 0.0,
        )

    def get_trace_timeline(self, trace_id: str) -> list:
        """按 timestamp 升序返回指定 trace_id 的所有事件"""
        events = [ev for ev in self._events if ev.trace_id == trace_id]
        events.sort(key=lambda e: e.timestamp)
        return events

    def get_overview(self, window_minutes: int = 5) -> List[StepStats]:
        """返回所有步骤的汇总统计，按 avg_ms 降序"""
        cutoff = time.time() - window_minutes * 60
        steps = set()
        for ev in self._events:
            if ev.timestamp >= cutoff:
                steps.add(ev.step)

        results = []
        for step in steps:
            stats = self.get_step_stats(step, window_minutes)
            if stats.count > 0:
                results.append(stats)

        results.sort(key=lambda s: s.avg_ms, reverse=True)
        return results


def get_metrics_collector() -> MetricsCollector:
    """获取 MetricsCollector 单例"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
