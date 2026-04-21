"""Anthropic 原生 provider adapter。"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, cast

import anthropic
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.profiles.anthropic import anthropic_model_profile
from pydantic_ai.providers.anthropic import AnthropicProvider

from src_deepagent.config.settings import get_settings
from src_deepagent.llm.compatibility import (
    max_tokens_for_execution_mode,
    thinking_level_for_execution_mode,
)
from src_deepagent.llm.providers.base import BaseProvider
from src_deepagent.llm.schemas import ModelProfile, ProviderConfig


class CompatibleAnthropicModel(AnthropicModel):
    """兼容 anthropic streaming 返回对象的 AnthropicModel。"""

    async def request(self, messages: list[Any], model_settings: Any | None, model_request_parameters: Any) -> Any:
        check_allow_model_requests = getattr(
            __import__("pydantic_ai.models.anthropic", fromlist=["check_allow_model_requests"]),
            "check_allow_model_requests",
        )
        check_allow_model_requests()
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        model_settings = cast(AnthropicModelSettings, model_settings or {})
        try:
            response = await self._messages_create(messages, False, model_settings, model_request_parameters)
            return self._process_response(response)
        except ValueError as e:
            if "Streaming is required" in str(e):
                stream = await self._messages_create(messages, True, model_settings, model_request_parameters)
                try:
                    streamed_response = await self._process_streamed_response(stream, model_request_parameters)
                    async for _ in streamed_response:
                        pass
                    return streamed_response.get()
                finally:
                    close = getattr(stream, "close", None)
                    if close is not None:
                        await close()
            raise

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[Any],
        model_settings: Any | None,
        model_request_parameters: Any,
        run_context: Any | None = None,
    ):
        check_allow_model_requests = getattr(
            __import__("pydantic_ai.models.anthropic", fromlist=["check_allow_model_requests"]),
            "check_allow_model_requests",
        )
        check_allow_model_requests()
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        response = await self._messages_create(
            messages, True, cast(AnthropicModelSettings, model_settings or {}), model_request_parameters
        )
        try:
            yield await self._process_streamed_response(response, model_request_parameters)
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                await close()

class AnthropicNativeProvider(BaseProvider):
    """Anthropic 原生协议 provider。"""

    def _canonical_profile_name(self, model_name: str) -> str:
        aliases = {
            "claude-4.5-haiku": "claude-haiku-4-5",
            "claude-4.6-sonnet": "claude-sonnet-4-6",
            "claude-4.6-opus": "claude-opus-4-6",
            "claude-4.7-opus": "claude-opus-4-7",
        }
        return aliases.get(model_name, model_name)

    def create_model(self, profile: ModelProfile, provider_cfg: ProviderConfig) -> Any:
        settings = get_settings()
        api_key = os.getenv(provider_cfg.api_key_env or "", "") or settings.llm.api_key
        base_url = os.getenv(provider_cfg.base_url_env or "", "") or settings.llm.base_url
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]

        anthropic_client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url or None,
            default_headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
                **provider_cfg.default_headers,
            },
        )
        provider = AnthropicProvider(anthropic_client=anthropic_client)
        model_profile = anthropic_model_profile(self._canonical_profile_name(profile.model))
        return CompatibleAnthropicModel(profile.model, provider=provider, profile=model_profile)

    def create_model_settings(self, profile: ModelProfile, execution_mode: str) -> Any | None:
        if not profile.capabilities.supports_native_thinking:
            return None
        max_tokens = max_tokens_for_execution_mode(execution_mode)
        return AnthropicModelSettings(
            thinking=thinking_level_for_execution_mode(execution_mode),
            max_tokens=max_tokens,
        )
