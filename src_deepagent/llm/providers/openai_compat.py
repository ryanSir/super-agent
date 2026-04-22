"""OpenAI 兼容 provider adapter。"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pydantic_ai.models.openai import OMIT, OpenAIModel, OpenAIModelSettings
from pydantic_ai.models import check_allow_model_requests
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart, ToolCallPart
from pydantic_ai.profiles.openai import OpenAIModelProfile, openai_model_profile
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RequestUsage

from src_deepagent.config.settings import get_settings
from src_deepagent.llm.compatibility import (
    max_tokens_for_execution_mode,
    thinking_level_for_execution_mode,
)
from src_deepagent.llm.providers.base import BaseProvider
from src_deepagent.llm.schemas import ModelProfile, ProviderConfig


def _drop_openai_omit(value: Any) -> Any:
    """递归移除 openai SDK 的 OMIT 哨兵，保证 payload 可序列化。"""
    if value is OMIT:
        return None
    if isinstance(value, dict):
        return {
            k: cleaned
            for k, v in value.items()
            if (cleaned := _drop_openai_omit(v)) is not None
        }
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _drop_openai_omit(item)) is not None]
    return value


class ReasoningContentOpenAIModel(OpenAIModel):
    """通过原始 JSON 解析 reasoning_content 的 OpenAI 兼容模型。

    用于绕过 openai SDK Chat Completions typed model 丢弃 `reasoning_content` 字段的问题。
    这里只修复非流式 `request()`；流式链路由业务层对该类模型禁用真流式。
    """

    async def request(self, messages: list[Any], model_settings: Any | None, model_request_parameters: Any) -> Any:
        check_allow_model_requests()
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        model_settings = model_settings or {}

        tools = self._get_tools(model_request_parameters)
        profile = OpenAIModelProfile.from_profile(self.profile)
        if not tools:
            tool_choice: str | None = None
        elif not model_request_parameters.allow_text_output and profile.openai_supports_tool_choice_required:
            tool_choice = "required"
        else:
            tool_choice = "auto"

        openai_messages = await self._map_messages(messages, model_request_parameters)
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": openai_messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
            if "parallel_tool_calls" in model_settings:
                payload["parallel_tool_calls"] = model_settings["parallel_tool_calls"]

        field_map = {
            "stop_sequences": "stop",
            "max_tokens": "max_completion_tokens",
            "seed": "seed",
            "openai_user": "user",
            "openai_service_tier": "service_tier",
            "openai_prediction": "prediction",
            "temperature": "temperature",
            "top_p": "top_p",
            "presence_penalty": "presence_penalty",
            "frequency_penalty": "frequency_penalty",
            "logit_bias": "logit_bias",
            "openai_logprobs": "logprobs",
            "openai_top_logprobs": "top_logprobs",
            "openai_store": "store",
            "openai_prompt_cache_key": "prompt_cache_key",
            "extra_body": "extra_body",
        }
        for src_key, dst_key in field_map.items():
            value = model_settings.get(src_key)
            if value is not None:
                payload[dst_key] = value

        reasoning_effort = self._translate_thinking(model_settings, model_request_parameters)
        if reasoning_effort is not None and reasoning_effort is not False:
            payload["reasoning_effort"] = reasoning_effort

        timeout = model_settings.get("timeout")
        headers = {
            k: v
            for k, v in {**getattr(self.client, "default_headers", {}), **model_settings.get("extra_headers", {})}.items()
            if isinstance(v, str)
        }
        raw_client = self.client._client  # pyright: ignore[reportPrivateUsage]
        url = f"{str(self.client.base_url).rstrip('/')}/chat/completions"
        response = await raw_client.post(
            url,
            headers=headers,
            json=_drop_openai_omit(payload),
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        return self._process_raw_response(body)

    def _process_raw_response(self, body: dict[str, Any]) -> ModelResponse:
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Invalid raw completion response: missing choices")
        choice = choices[0]
        message = choice.get("message") or {}
        parts: list[Any] = []

        reasoning = message.get("reasoning_content") or message.get("reasoning")
        if isinstance(reasoning, str) and reasoning:
            parts.append(ThinkingPart(id="reasoning_content", content=reasoning, provider_name=self.system))

        content = message.get("content")
        if isinstance(content, str) and content:
            parts.append(TextPart(content))

        tool_calls = message.get("tool_calls") or []
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments")
            tool_call_id = tool_call.get("id")
            if name and arguments is not None:
                parts.append(ToolCallPart(name, arguments, tool_call_id=tool_call_id))

        usage = body.get("usage") or {}
        provider_details: dict[str, Any] = {}
        finish_reason = choice.get("finish_reason")
        if finish_reason:
            provider_details["finish_reason"] = finish_reason
        return ModelResponse(
            parts=parts,
            usage=RequestUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                details={
                    k: v
                    for k, v in (
                        ("reasoning_tokens", ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0))),
                    )
                    if v
                },
            ),
            model_name=body.get("model") or self.model_name,
            timestamp=datetime.now(timezone.utc),
            provider_details=provider_details or None,
            provider_response_id=body.get("id"),
            provider_name=self._provider.name,
            provider_url=self._provider.base_url,
            finish_reason=finish_reason,
        )


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
        if profile.reasoning_format == "reasoning_content":
            return ReasoningContentOpenAIModel(profile.model, provider=provider, profile=self._build_profile(profile))
        return OpenAIModel(profile.model, provider=provider, profile=self._build_profile(profile))

    def create_model_settings(self, profile: ModelProfile, execution_mode: str) -> Any | None:
        max_tokens = max_tokens_for_execution_mode(execution_mode)
        if profile.capabilities.reasoning:
            return OpenAIModelSettings(
                openai_reasoning_effort=thinking_level_for_execution_mode(execution_mode),
                max_tokens=max_tokens,
            )
        return OpenAIModelSettings(max_tokens=max_tokens)
