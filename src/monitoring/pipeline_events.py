"""管道事件日志

标准化的关键步骤事件记录，提供 pipeline_step 上下文管理器和 log_pipeline_step 装饰器。
事件同时输出到结构化日志和可选的 Langfuse span。
"""

# 标准库
import asyncio
import functools
import re
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, Generator, Optional

# 本地模块
from src.core.logging import get_logger, request_id_var, trace_id_var

logger = get_logger(__name__)

# 步骤命名校验：点分层级
_STEP_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class EventStatus(str, Enum):
    """事件状态"""
    started = "started"
    completed = "completed"
    failed = "failed"


@dataclass
class PipelineEvent:
    """管道事件数据模型"""
    trace_id: str
    request_id: str
    session_id: str
    step: str
    status: EventStatus
    timestamp: float
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, **kwargs: Any) -> None:
        """追加 metadata"""
        self.metadata.update(kwargs)

    def to_log_string(self) -> str:
        """输出结构化日志行"""
        parts = [
            f"step={self.step}",
            f"status={self.status.value}",
        ]
        if self.duration_ms is not None:
            parts.append(f"duration_ms={self.duration_ms:.1f}")
        for k, v in self.metadata.items():
            parts.append(f"{k}={v}")
        return "PIPELINE_EVENT | " + " ".join(parts)


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


def _validate_step_name(step: str) -> None:
    """校验步骤命名规范，不合规时记录 warning"""
    if not _STEP_PATTERN.match(step):
        logger.warning(f"[PipelineEvent] 步骤命名不规范 | step={step} (应为点分层级如 worker.native.rag)")


def _emit_event(event: PipelineEvent) -> None:
    """输出事件到结构化日志 + 指标采集

    Langfuse 专注 LLM 交互监控（由 PydanticAI 自动上报），
    业务步骤耗时通过日志和 metrics 采集。
    """
    try:
        logger.info(event.to_log_string())
    except Exception as e:
        logger.warning(f"[PipelineEvent] 日志输出失败 | error={e}")

    # 指标采集
    try:
        from src.monitoring.execution_metrics import get_metrics_collector
        get_metrics_collector().record(event)
    except Exception:
        pass


def _get_session_id() -> str:
    """从 ContextVar 获取 session_id"""
    try:
        from src.core.logging import session_id_var
        return session_id_var.get("")
    except (ImportError, AttributeError):
        return ""


@asynccontextmanager
async def pipeline_step(
    step: str,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> AsyncGenerator[PipelineEvent, None]:
    """异步上下文管理器，自动记录步骤的 started/completed/failed 事件

    Args:
        step: 步骤标识（点分层级命名）
        metadata: 初始 metadata
        session_id: 会话 ID（可选，优先使用 ContextVar）
    """
    _validate_step_name(step)

    sid = session_id or _get_session_id()
    event = PipelineEvent(
        trace_id=trace_id_var.get(""),
        request_id=request_id_var.get(""),
        session_id=sid,
        step=step,
        status=EventStatus.started,
        timestamp=time.time(),
        metadata=dict(metadata) if metadata else {},
    )

    try:
        _emit_event(event)
    except Exception:
        pass

    start = time.monotonic()
    try:
        yield event
        elapsed = (time.monotonic() - start) * 1000
        event.status = EventStatus.completed
        event.duration_ms = elapsed
        event.timestamp = time.time()
        # 慢查询标记
        if elapsed > 5000:
            event.add_metadata(slow=True)
        try:
            _emit_event(event)
        except Exception:
            pass
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        event.status = EventStatus.failed
        event.duration_ms = elapsed
        event.timestamp = time.time()
        event.add_metadata(error_type=type(exc).__name__, error_msg=str(exc)[:200])
        try:
            _emit_event(event)
        except Exception:
            pass
        raise


@contextmanager
def pipeline_step_sync(
    step: str,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> Generator[PipelineEvent, None, None]:
    """同步上下文管理器"""
    _validate_step_name(step)

    sid = session_id or _get_session_id()
    event = PipelineEvent(
        trace_id=trace_id_var.get(""),
        request_id=request_id_var.get(""),
        session_id=sid,
        step=step,
        status=EventStatus.started,
        timestamp=time.time(),
        metadata=dict(metadata) if metadata else {},
    )

    try:
        _emit_event(event)
    except Exception:
        pass

    start = time.monotonic()
    try:
        yield event
        elapsed = (time.monotonic() - start) * 1000
        event.status = EventStatus.completed
        event.duration_ms = elapsed
        event.timestamp = time.time()
        if elapsed > 5000:
            event.add_metadata(slow=True)
        try:
            _emit_event(event)
        except Exception:
            pass
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        event.status = EventStatus.failed
        event.duration_ms = elapsed
        event.timestamp = time.time()
        event.add_metadata(error_type=type(exc).__name__, error_msg=str(exc)[:200])
        try:
            _emit_event(event)
        except Exception:
            pass
        raise


def log_pipeline_step(step: str, **extra_metadata: Any) -> Callable:
    """装饰器，自动记录函数执行事件，支持 sync/async"""
    def decorator(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with pipeline_step(step, metadata=extra_metadata):
                    return await fn(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with pipeline_step_sync(step, metadata=extra_metadata):
                    return fn(*args, **kwargs)
            return sync_wrapper
    return decorator
