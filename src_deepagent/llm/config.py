"""LLM 模型工厂

通过 PydanticAI OpenAIModel 对接 rd-gateway（OpenAI 兼容协议 → Bedrock Claude）。
"""

from __future__ import annotations

from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

# ── 模型别名映射 ─────────────────────────────────────────

_MODEL_ALIASES: dict[str, str] = {}


def _init_aliases() -> None:
    """从配置初始化模型别名"""
    global _MODEL_ALIASES  # noqa: PLW0603
    settings = get_settings()
    _MODEL_ALIASES = {
        "planning": settings.llm.planning_model,
        "execution": settings.llm.execution_model,
        "fast": settings.llm.fast_model,
    }


def _ensure_aliases() -> None:
    if not _MODEL_ALIASES:
        _init_aliases()


# ── 模型工厂 ──────────────────────────────────────────────


def get_model(alias: str) -> Any:
    """根据别名获取 PydanticAI Model 对象

    Claude 模型走 Anthropic 原生路径（支持 extended thinking）；
    其他模型走 OpenAI 兼容路径。
    """
    _ensure_aliases()
    settings = get_settings()
    model_name = _MODEL_ALIASES.get(alias, alias)

    is_claude = "claude" in model_name.lower()

    if is_claude and settings.llm.base_url:
        import anthropic
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        # rd-gateway 用 Bearer token，base_url 去掉 /v1 后缀
        base = settings.llm.base_url
        if base.endswith("/v1"):
            base = base[:-3]

        anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.llm.api_key,
            base_url=base,
            default_headers={
                "Authorization": f"Bearer {settings.llm.api_key}",
                "x-api-key": settings.llm.api_key,
            },
        )
        provider = AnthropicProvider(anthropic_client=anthropic_client)
        model = AnthropicModel(model_name, provider=provider)
        logger.info(
            f"模型创建 | alias={alias} → model={model_name} "
            f"path=anthropic_native base_url={base}"
        )
    else:
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url or None,
        )
        model = OpenAIModel(model_name, provider=provider)
        logger.info(
            f"模型创建 | alias={alias} → model={model_name} "
            f"path=openai_compat base_url={settings.llm.base_url or 'default'}"
        )

    return model


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
