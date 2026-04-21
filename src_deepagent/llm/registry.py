"""LLM registry 门面。"""

from __future__ import annotations

from src_deepagent.core.logging import get_logger
from src_deepagent.llm.catalog import get_catalog
from src_deepagent.llm.providers.anthropic_native import AnthropicNativeProvider
from src_deepagent.llm.providers.base import BaseProvider
from src_deepagent.llm.providers.openai_compat import OpenAICompatProvider
from src_deepagent.llm.schemas import ModelBundle, ModelProfile, ProviderConfig

logger = get_logger(__name__)

_PROVIDERS: dict[str, BaseProvider] = {
    "openai_compat": OpenAICompatProvider(),
    "anthropic_native": AnthropicNativeProvider(),
}


def _resolve_profile(role_or_model: str) -> tuple[ModelProfile, ProviderConfig]:
    catalog = get_catalog()
    profile_name = catalog.roles.get(role_or_model, role_or_model)
    if profile_name not in catalog.models:
        raise KeyError(f"未找到模型角色或档案: {role_or_model}")
    profile = catalog.models[profile_name]
    if profile.provider not in catalog.providers:
        raise KeyError(f"未找到 provider: {profile.provider}")
    provider = catalog.providers[profile.provider]
    return profile, provider


def get_model_bundle(role: str, execution_mode: str = "auto") -> ModelBundle:
    """根据角色或模型档案获取模型包。"""
    profile, provider_cfg = _resolve_profile(role)
    adapter = _PROVIDERS[provider_cfg.kind]
    model = adapter.create_model(profile, provider_cfg)
    model_settings = adapter.create_model_settings(profile, execution_mode)
    logger.info(
        f"模型创建 | role={role} profile={profile.name} model={profile.model} "
        f"provider={provider_cfg.kind} execution_mode={execution_mode}"
    )
    return ModelBundle(
        model=model,
        profile=profile,
        provider=provider_cfg,
        model_settings=model_settings,
    )


def get_model_for_role(role: str):
    """兼容旧调用，只返回模型对象。"""
    return get_model_bundle(role).model
