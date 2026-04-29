"""Reusable model factories for learning demos."""

from __future__ import annotations

import os
from collections.abc import Callable

import dotenv
from anthropic import AsyncAnthropic
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider


def _load_env() -> None:
    dotenv.load_dotenv()


def _clear_anthropic_sdk_env() -> None:
    """Avoid Claude Code env vars overriding explicitly configured clients."""
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    os.environ.pop("ANTHROPIC_BASE_URL", None)


def create_gateway_claude_sonnet_46_model() -> AnthropicModel:
    _load_env()
    token = os.environ["OPENAI_API_KEY"]

    anthropic_client = AsyncAnthropic(
        api_key=token,
        base_url="http://rd-gateway.patsnap.info",
        default_headers={
            "Authorization": f"Bearer {token}",
            "x-api-key": token,
        },
    )

    return AnthropicModel(
        "claude-4.6-sonnet",
        provider=AnthropicProvider(anthropic_client=anthropic_client),
    )


def create_gateway_claude_opus_46_model() -> AnthropicModel:
    _load_env()
    token = os.environ["OPENAI_API_KEY"]

    anthropic_client = AsyncAnthropic(
        api_key=token,
        base_url="http://rd-gateway.patsnap.info",
        default_headers={
            "Authorization": f"Bearer {token}",
            "x-api-key": token,
        },
    )

    return AnthropicModel(
        "claude-4.6-opus",
        provider=AnthropicProvider(anthropic_client=anthropic_client),
    )


def create_gateway_openai_gpt_54_model() -> OpenAIChatModel:
    _load_env()
    token = os.environ["OPENAI_API_KEY"]
    base_url = os.environ.get("OPENAI_API_BASE") or "http://rd-gateway.patsnap.info/v1"

    return OpenAIChatModel(
        "gpt-5.4",
        provider=OpenAIProvider(
            api_key=token,
            base_url=base_url,
        ),
    )


def create_close_ai_openai_gpt_54_model() -> OpenAIChatModel:
    _load_env()
    token = os.environ.get("CLOSE_AI_OPENAI_API_KEY") or os.environ["CLOSE_AI_ANTHROPIC_API_KEY"]
    base_url = os.environ.get("CLOSE_AI_OPENAI_BASE_URL") or "https://api.openai-proxy.org/v1"

    return OpenAIChatModel(
        "gpt-5.4",
        provider=OpenAIProvider(
            api_key=token,
            base_url=base_url,
        ),
    )


def create_close_ai_claude_sonnet_46_model() -> AnthropicModel:
    _load_env()
    token = os.environ.get("CLOSE_AI_ANTHROPIC_API_KEY")

    _clear_anthropic_sdk_env()

    anthropic_client = AsyncAnthropic(
        api_key=token,
        base_url="https://api.openai-proxy.org/anthropic",
        default_headers={
            "x-api-key": token,
        },
    )

    return AnthropicModel(
        "claude-sonnet-4-6",
        provider=AnthropicProvider(anthropic_client=anthropic_client),
    )


MODEL_FACTORIES: dict[str, Callable[[], AnthropicModel | OpenAIChatModel]] = {
    "gateway-claude-opus-4.6": create_gateway_claude_opus_46_model,
    "gateway-claude-sonnet-4.6": create_gateway_claude_sonnet_46_model,
    "gateway-openai-gpt-5.4": create_gateway_openai_gpt_54_model,
    "close-ai-claude-sonnet-4.6": create_close_ai_claude_sonnet_46_model,
    "close-ai-openai-gpt-5.4": create_close_ai_openai_gpt_54_model,
}


def create_model(name: str) -> AnthropicModel | OpenAIChatModel:
    model_name = name
    try:
        factory = MODEL_FACTORIES[model_name]
    except KeyError as exc:
        choices = ", ".join(sorted(MODEL_FACTORIES))
        raise ValueError(f"Unknown demo model: {model_name}. Choices: {choices}") from exc
    return factory()
