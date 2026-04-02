"""LLM 模型配置

通过 OpenAI 兼容网关路由 Claude 模型，PydanticAI 直接消费。
配置 Langfuse 回调实现零代码侵入的全链路追踪。
"""

# 标准库
import os
from typing import Dict

# 第三方库
import litellm
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 缓存的模型实例
_model_cache: Dict[str, OpenAIModel] = {}


def get_model(alias: str = "planning") -> OpenAIModel:
    """获取 PydanticAI 模型实例

    通过 OpenAI 兼容网关（rd-gateway）路由到 Claude 模型。

    Args:
        alias: 模型别名（planning / execution / fast）

    Returns:
        OpenAIModel 实例
    """
    if alias in _model_cache:
        return _model_cache[alias]

    settings = get_settings()

    # 模型别名 → 实际模型名称（通过 OpenAI 兼容网关路由）
    model_names = {
        "planning": settings.llm.planning_model,
        "execution": settings.llm.execution_model,
        "fast": settings.llm.fast_model,
    }
    model_name = model_names.get(alias, settings.llm.claude_model)

    model = OpenAIModel(
        model_name,
        provider=OpenAIProvider(
            base_url=settings.llm.openai_api_base,
            api_key=settings.llm.openai_api_key,
        ),
    )

    _model_cache[alias] = model

    logger.info(
        f"[LLM] 创建模型实例 | alias={alias} model={model_name} "
        f"gateway={settings.llm.openai_api_base}"
    )
    return model


def setup_litellm() -> None:
    """初始化 LiteLLM 全局配置（Langfuse 回调等）"""
    settings = get_settings()

    # OpenAI 兼容网关配置
    os.environ["OPENAI_API_KEY"] = settings.llm.openai_api_key
    os.environ["OPENAI_API_BASE"] = settings.llm.openai_api_base

    # Langfuse 回调
    if settings.langfuse.is_configured:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = settings.langfuse.langfuse_host
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
        logger.info("[LLM] Langfuse 回调已注册")

    litellm.set_verbose = False
    litellm.request_timeout = 60
    litellm.num_retries = 2

    logger.info(
        f"[LLM] 初始化完成 | gateway={settings.llm.openai_api_base} "
        f"model={settings.llm.claude_model}"
    )
