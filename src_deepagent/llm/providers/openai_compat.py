"""OpenAI 兼容 provider adapter。"""

from __future__ import annotations

import os
from typing import Any

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.profiles.openai import OpenAIModelProfile, openai_model_profile
from pydantic_ai.providers.openai import OpenAIProvider

from src_deepagent.config.settings import get_settings
from src_deepagent.llm.providers.base import BaseProvider
from src_deepagent.llm.schemas import ModelProfile, ProviderConfig


class OpenAICompatProvider(BaseProvider):
    """OpenAI 兼容协议 provider。"""

    def _build_profile(self, profile: ModelProfile) -> OpenAIModelProfile:
        base_profile = openai_model_profile(profile.model)

        if profile.reasoning_format == "reasoning_content":
            return base_profile.update(
                OpenAIModelProfile(
                    openai_chat_thinking_field="reasoning_content",
                    openai_chat_send_back_thinking_parts="field",
                )
            )

        if profile.reasoning_format == "inline_thinking_tags":
            return base_profile.update(
                OpenAIModelProfile(
                    thinking_tags=("<thinking>", "</thinking>"),
                    openai_chat_send_back_thinking_parts="tags",
                )
            )

        return base_profile

    def create_model(self, profile: ModelProfile, provider_cfg: ProviderConfig) -> Any:
        settings = get_settings()
        api_key = os.getenv(provider_cfg.api_key_env or "", "") or settings.llm.api_key
        base_url = os.getenv(provider_cfg.base_url_env or "", "") or settings.llm.base_url or None
        provider = OpenAIProvider(
            api_key=api_key,
            base_url=base_url,
        )
        return OpenAIModel(profile.model, provider=provider, profile=self._build_profile(profile))

    def create_model_settings(self, profile: ModelProfile, execution_mode: str) -> Any | None:
        return None
