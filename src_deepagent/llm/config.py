"""LLM 模型兼容层。"""

from __future__ import annotations

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.llm.registry import get_model_for_role

logger = get_logger(__name__)


def get_model(alias: str):
    """兼容旧接口。"""
    return get_model_for_role(alias)


def configure_litellm() -> None:
    """配置 LiteLLM 全局参数（兼容保留）"""
    settings = get_settings()
    if not settings.llm.enable_litellm:
        logger.info("LLM 配置完成 | litellm=disabled（设置 ENABLE_LITELLM=true 启用）")
        return
    try:
        import litellm

        litellm.request_timeout = settings.llm.request_timeout
        if settings.llm.api_key:
            litellm.api_key = settings.llm.api_key
        if settings.llm.base_url:
            litellm.api_base = settings.llm.base_url
    except ImportError:
        pass
    logger.info(
        f"LLM 配置完成 | timeout={settings.llm.request_timeout}s "
        f"base_url={settings.llm.base_url or 'default'}"
    )
