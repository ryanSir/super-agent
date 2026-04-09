"""Langfuse 追踪集成"""

from __future__ import annotations

from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

_client: Any = None


def get_langfuse() -> Any | None:
    """获取 Langfuse 客户端（懒初始化）"""
    global _client  # noqa: PLW0603
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.langfuse.enabled:
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse.public_key,
            secret_key=settings.langfuse.secret_key,
            host=settings.langfuse.host,
        )
        logger.info(f"Langfuse 初始化完成 | host={settings.langfuse.host}")
        return _client
    except ImportError:
        logger.warning("langfuse 未安装")
        return None
    except Exception as e:
        logger.warning(f"Langfuse 初始化失败 | error={e}")
        return None


def create_trace(
    name: str,
    session_id: str = "",
    trace_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> Any | None:
    """创建 Langfuse Trace"""
    client = get_langfuse()
    if not client:
        return None

    return client.trace(
        name=name,
        id=trace_id or None,
        session_id=session_id or None,
        metadata=metadata or {},
    )


def flush() -> None:
    """刷新 Langfuse 缓冲区"""
    if _client:
        try:
            _client.flush()
        except Exception as e:
            logger.warning(f"Langfuse flush 失败 | error={e}")
