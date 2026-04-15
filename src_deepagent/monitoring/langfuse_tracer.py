"""Langfuse 全链路追踪集成（v4 API）

提供 @observe 装饰器包装、手动 Span 上下文管理、统一初始化与降级。
未启用时所有追踪函数为 no-op，零开销。
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_client: Any = None
_enabled: bool = False


def configure_langfuse() -> None:
    """初始化 Langfuse 客户端（应用启动时调用一次）"""
    global _client, _enabled  # noqa: PLW0603

    settings = get_settings()
    if not settings.langfuse.enabled:
        logger.info("Langfuse 追踪未启用 | 设置 LANGFUSE_ENABLED=true 启用")
        return

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse.public_key,
            secret_key=settings.langfuse.secret_key,
            host=settings.langfuse.host,
        )
        # 抑制 OTel attributes 的 Omit 类型警告（Anthropic SDK 兼容性问题）
        import logging
        logging.getLogger("opentelemetry.attributes").setLevel(logging.ERROR)

        _enabled = True
        logger.info(f"Langfuse 初始化完成 | host={settings.langfuse.host}")

        # 激活 Anthropic OTel 自动埋点，LLM 调用自动生成 Generation
        try:
            from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
            AnthropicInstrumentor().instrument()
            logger.info("Anthropic OTel 自动埋点已激活")
        except ImportError:
            logger.info("opentelemetry-instrumentation-anthropic 未安装，LLM Generation 需手动追踪")
        except Exception as e:
            logger.warning(f"Anthropic OTel 埋点激活失败 | error={e}")
    except ImportError:
        logger.warning("langfuse 未安装，追踪已禁用")
    except Exception as e:
        logger.warning(f"Langfuse 初始化失败 | error={e}")


def get_langfuse() -> Any | None:
    """获取 Langfuse 客户端"""
    return _client if _enabled else None


def is_enabled() -> bool:
    """追踪是否启用"""
    return _enabled


# ── @observe 装饰器包装 ──────────────────────────────────────


def traced(
    *,
    name: str | None = None,
    as_type: str = "span",
    capture_input: bool | None = None,
    capture_output: bool | None = None,
) -> Callable[[F], F]:
    """条件性 @observe 装饰器：启用时追踪，未启用时透传原函数"""

    def decorator(func: F) -> F:
        if not _enabled:
            return func

        from langfuse import observe

        return observe(
            func,
            name=name or func.__name__,
            as_type=as_type,
            capture_input=capture_input,
            capture_output=capture_output,
        )

    return decorator


# ── 手动 Span 上下文管理 ─────────────────────────────────────


@contextmanager
def trace_span(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
    level: str | None = None,
    status_message: str | None = None,
    model: str | None = None,
    usage_details: dict[str, int] | None = None,
):
    """手动创建追踪 Span 的上下文管理器

    未启用时 yield None，不产生任何开销。
    """
    if not _enabled or not _client:
        yield None
        return

    kwargs: dict[str, Any] = {"name": name, "as_type": as_type}
    if input is not None:
        kwargs["input"] = input
    if output is not None:
        kwargs["output"] = output
    if metadata is not None:
        kwargs["metadata"] = metadata
    if level is not None:
        kwargs["level"] = level
    if status_message is not None:
        kwargs["status_message"] = status_message
    if model is not None:
        kwargs["model"] = model
    if usage_details is not None:
        kwargs["usage_details"] = usage_details

    try:
        with _client.start_as_current_observation(**kwargs) as span:
            yield span
    except Exception as e:
        logger.warning(f"Langfuse span 异常 | name={name} error={e}")
        yield None


def update_current_span(
    *,
    output: Any = None,
    metadata: Any = None,
    level: str | None = None,
    status_message: str | None = None,
) -> None:
    """更新当前活跃 Span"""
    if not _enabled or not _client:
        return
    try:
        kwargs: dict[str, Any] = {}
        if output is not None:
            kwargs["output"] = output
        if metadata is not None:
            kwargs["metadata"] = metadata
        if level is not None:
            kwargs["level"] = level
        if status_message is not None:
            kwargs["status_message"] = status_message
        _client.update_current_span(**kwargs)
    except Exception as e:
        logger.warning(f"Langfuse update_current_span 失败 | error={e}")


def update_current_generation(
    *,
    output: Any = None,
    model: str | None = None,
    usage_details: dict[str, int] | None = None,
    level: str | None = None,
    status_message: str | None = None,
) -> None:
    """更新当前活跃 Generation"""
    if not _enabled or not _client:
        return
    try:
        kwargs: dict[str, Any] = {}
        if output is not None:
            kwargs["output"] = output
        if model is not None:
            kwargs["model"] = model
        if usage_details is not None:
            kwargs["usage_details"] = usage_details
        if level is not None:
            kwargs["level"] = level
        if status_message is not None:
            kwargs["status_message"] = status_message
        _client.update_current_generation(**kwargs)
    except Exception as e:
        logger.warning(f"Langfuse update_current_generation 失败 | error={e}")


def score_current_trace(
    *,
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    """为当前 Trace 打分"""
    if not _enabled or not _client:
        return
    try:
        _client.score_current_trace(name=name, value=value, comment=comment)
    except Exception as e:
        logger.warning(f"Langfuse score 失败 | error={e}")


# ── 生命周期 ─────────────────────────────────────────────────


def flush() -> None:
    """刷新 Langfuse 缓冲区"""
    if _client:
        try:
            _client.flush()
        except Exception as e:
            logger.warning(f"Langfuse flush 失败 | error={e}")


def shutdown() -> None:
    """关闭 Langfuse 客户端"""
    global _client, _enabled  # noqa: PLW0603
    if _client:
        try:
            _client.flush()
            _client.shutdown()
        except Exception as e:
            logger.warning(f"Langfuse shutdown 失败 | error={e}")
        finally:
            _client = None
            _enabled = False
