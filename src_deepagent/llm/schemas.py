"""LLM 配置数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelCapabilities(BaseModel):
    """模型能力描述。"""

    streaming: bool = True
    tool_calling: bool = True
    reasoning: bool = False
    supports_native_thinking: bool = False
    requires_reasoning_content_on_tool_call: bool = False


class ProviderConfig(BaseModel):
    """Provider 配置。"""

    name: str
    kind: Literal["openai_compat", "anthropic_native"]
    api_key_env: str | None = None
    base_url_env: str | None = None
    default_headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = 60


class ModelProfile(BaseModel):
    """模型档案。"""

    name: str
    provider: str
    model: str
    transport: Literal["openai_compat", "anthropic_native"]
    reasoning_format: Literal[
        "none",
        "anthropic_thinking",
        "inline_thinking_tags",
        "reasoning_content",
    ] = "none"
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    default_params: dict[str, Any] = Field(default_factory=dict)


class ModelCatalog(BaseModel):
    """模型目录。"""

    providers: dict[str, ProviderConfig]
    models: dict[str, ModelProfile]
    roles: dict[str, str]


@dataclass(frozen=True)
class ModelBundle:
    """业务侧消费的模型包。"""

    model: Any
    profile: ModelProfile
    provider: ProviderConfig
    model_settings: Any | None = None
