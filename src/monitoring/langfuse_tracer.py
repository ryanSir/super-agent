"""Langfuse 集成

单例模式管理 Langfuse 客户端，提供 trace/span 上下文管理器。
"""

# 标准库
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 单例
_langfuse_client = None
_initialized = False


def get_langfuse():
    """获取 Langfuse 客户端单例

    Returns:
        Langfuse 客户端实例，未配置时返回 None
    """
    global _langfuse_client, _initialized

    if _initialized:
        return _langfuse_client

    _initialized = True
    settings = get_settings()

    if not settings.langfuse.is_configured:
        logger.info("[Langfuse] 未配置，跳过初始化")
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse.langfuse_public_key,
            secret_key=settings.langfuse.langfuse_secret_key,
            host=settings.langfuse.langfuse_host,
        )
        logger.info(
            f"[Langfuse] 初始化完成 | host={settings.langfuse.langfuse_host}"
        )
    except Exception as e:
        logger.warning(f"[Langfuse] 初始化失败，降级运行 | error={e}")
        _langfuse_client = None

    return _langfuse_client


@contextmanager
def trace_context(
    name: str,
    trace_id: str,
    session_id: str = "",
    user_id: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Generator:
    """Langfuse Trace 上下文管理器

    Args:
        name: Trace 名称
        trace_id: 全链路追踪 ID
        session_id: 会话 ID
        user_id: 用户 ID
        metadata: 附加元数据

    Yields:
        Langfuse trace 对象，未配置时 yield None

    Example:
        >>> with trace_context("query_execution", trace_id="req-123") as trace:
        ...     if trace:
        ...         span = trace.span(name="planning")
    """
    client = get_langfuse()
    trace = None

    if client:
        try:
            trace = client.trace(
                id=trace_id,
                name=name,
                session_id=session_id or None,
                user_id=user_id or None,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.warning(f"[Langfuse] 创建 Trace 失败 | error={e}")

    try:
        yield trace
    finally:
        if client:
            try:
                client.flush()
            except Exception:
                pass


@contextmanager
def observation_span(
    trace,
    name: str,
    span_type: str = "span",
    input_data: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Generator:
    """Langfuse Observation Span 上下文管理器

    Args:
        trace: 父 Trace 对象
        name: Span 名称
        span_type: span 类型（span / generation）
        input_data: 输入数据
        metadata: 附加元数据

    Yields:
        Langfuse span 对象
    """
    span = None

    if trace:
        try:
            if span_type == "generation":
                span = trace.generation(
                    name=name,
                    input=input_data,
                    metadata=metadata or {},
                )
            else:
                span = trace.span(
                    name=name,
                    input=input_data,
                    metadata=metadata or {},
                )
        except Exception as e:
            logger.warning(f"[Langfuse] 创建 Span 失败 | name={name} error={e}")

    try:
        yield span
    finally:
        if span:
            try:
                span.end()
            except Exception:
                pass
