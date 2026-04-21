"""LLM 模型目录加载。"""

from __future__ import annotations

from pathlib import Path

import yaml

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.llm.schemas import ModelCatalog, ModelProfile, ProviderConfig

logger = get_logger(__name__)

_CATALOG: ModelCatalog | None = None


def _load_from_yaml(path: Path) -> ModelCatalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    providers = {
        name: ProviderConfig(name=name, **data)
        for name, data in (raw.get("providers") or {}).items()
    }
    models = {
        name: ModelProfile(name=name, **data)
        for name, data in (raw.get("models") or {}).items()
    }
    roles = dict(raw.get("roles") or {})

    return ModelCatalog(providers=providers, models=models, roles=roles)


def _build_legacy_catalog() -> ModelCatalog:
    settings = get_settings()

    provider = ProviderConfig(
        name="legacy_gateway",
        kind="openai_compat",
        api_key_env="OPENAI_API_KEY",
        base_url_env="OPENAI_API_BASE",
        timeout=settings.llm.request_timeout,
    )
    models = {
        "orchestrator": ModelProfile(
            name="orchestrator",
            provider=provider.name,
            model=settings.llm.orchestrator_model,
            transport="anthropic_native" if "claude" in settings.llm.orchestrator_model.lower() else "openai_compat",
            reasoning_format="anthropic_thinking" if "claude" in settings.llm.orchestrator_model.lower() else "none",
        ),
        "subagent": ModelProfile(
            name="subagent",
            provider=provider.name,
            model=settings.llm.subagent_model,
            transport="anthropic_native" if "claude" in settings.llm.subagent_model.lower() else "openai_compat",
            reasoning_format="anthropic_thinking" if "claude" in settings.llm.subagent_model.lower() else "none",
        ),
        "classifier": ModelProfile(
            name="classifier",
            provider=provider.name,
            model=settings.llm.classifier_model,
            transport="anthropic_native" if "claude" in settings.llm.classifier_model.lower() else "openai_compat",
            reasoning_format="anthropic_thinking" if "claude" in settings.llm.classifier_model.lower() else "none",
        ),
        "planner": ModelProfile(
            name="planner",
            provider=provider.name,
            model=settings.llm.orchestrator_model,
            transport="anthropic_native" if "claude" in settings.llm.orchestrator_model.lower() else "openai_compat",
            reasoning_format="anthropic_thinking" if "claude" in settings.llm.orchestrator_model.lower() else "none",
        ),
    }
    roles = {
        "orchestrator": "orchestrator",
        "subagent": "subagent",
        "classifier": "classifier",
        "planner": "planner",
    }
    logger.warning("LLM catalog 使用 legacy env fallback")
    return ModelCatalog(providers={provider.name: provider}, models=models, roles=roles)


def load_catalog(path: str | None = None) -> ModelCatalog:
    """加载模型目录并缓存。"""
    global _CATALOG  # noqa: PLW0603

    settings = get_settings()
    catalog_path = Path(path or settings.llm.config_path)
    if catalog_path.exists():
        _CATALOG = _load_from_yaml(catalog_path)
        logger.info(
            f"LLM catalog 加载完成 | path={catalog_path} "
            f"providers={len(_CATALOG.providers)} models={len(_CATALOG.models)} roles={len(_CATALOG.roles)}"
        )
    else:
        _CATALOG = _build_legacy_catalog()
    return _CATALOG


def get_catalog() -> ModelCatalog:
    """获取模型目录。"""
    global _CATALOG  # noqa: PLW0603
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


def reload_catalog(path: str | None = None) -> ModelCatalog:
    """重新加载模型目录。"""
    return load_catalog(path)
