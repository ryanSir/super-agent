"""应用配置

基于 Pydantic BaseSettings，通过环境变量绑定所有配置项。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM 模型配置"""

    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    base_url: str = Field(default="", alias="OPENAI_API_BASE")
    planning_model: str = Field(default="claude-4.5-sonnet", alias="PLANNING_MODEL")
    execution_model: str = Field(default="gpt-4o-mini", alias="EXECUTION_MODEL")
    fast_model: str = Field(default="gpt-4o-mini", alias="FAST_MODEL")
    request_timeout: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT")
    enable_litellm: bool = Field(default=False, alias="ENABLE_LITELLM")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class RedisSettings(BaseSettings):
    """Redis 配置"""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    stream_max_len: int = Field(default=5000, alias="REDIS_STREAM_MAX_LEN")
    stream_ttl: int = Field(default=3600, alias="REDIS_STREAM_TTL")

    @property
    def url(self) -> str:
        """构建 Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class E2BSettings(BaseSettings):
    """E2B 沙箱配置"""

    api_key: str = Field(default="", alias="E2B_API_KEY")
    timeout: int = Field(default=300, alias="E2B_TIMEOUT")
    use_local: bool = Field(default=True, alias="E2B_USE_LOCAL")
    sandbox_pi_provider: str = Field(default="my-gateway", alias="SANDBOX_PI_PROVIDER")
    sandbox_pi_model: str = Field(default="gpt-4o", alias="SANDBOX_PI_MODEL")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class LangfuseSettings(BaseSettings):
    """Langfuse 可观测性配置"""

    public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")
    enabled: bool = Field(default=False, alias="LANGFUSE_ENABLED")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class MilvusSettings(BaseSettings):
    """Milvus 向量数据库配置"""

    host: str = Field(default="localhost", alias="MILVUS_HOST")
    port: int = Field(default=19530, alias="MILVUS_PORT")
    collection: str = Field(default="documents", alias="MILVUS_COLLECTION")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class MemorySettings(BaseSettings):
    """记忆系统配置"""

    enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    retrieval_timeout_ms: int = Field(default=200, alias="MEMORY_RETRIEVAL_TIMEOUT_MS")
    max_facts: int = Field(default=100, alias="MEMORY_MAX_FACTS")
    lock_ttl: int = Field(default=30, alias="MEMORY_LOCK_TTL")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class ReasoningSettings(BaseSettings):
    """推理引擎配置"""

    # LLM 兜底：模糊区间阈值
    fuzzy_zone_low: float = Field(default=0.35, alias="REASONING_FUZZY_ZONE_LOW")
    fuzzy_zone_high: float = Field(default=0.55, alias="REASONING_FUZZY_ZONE_HIGH")
    llm_classify_timeout: float = Field(default=5.0, alias="REASONING_LLM_CLASSIFY_TIMEOUT")
    llm_classify_enabled: bool = Field(default=True, alias="REASONING_LLM_CLASSIFY_ENABLED")

    # 模式升级
    escalation_enabled: bool = Field(default=False, alias="REASONING_ESCALATION_ENABLED")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class AppSettings(BaseSettings):
    """应用全局配置"""

    app_name: str = Field(default="super-agent", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")
    skill_dir: str = Field(default="skill", alias="SKILL_DIR")
    jwt_secret: str = Field(default="super-agent-secret", alias="JWT_SECRET")
    max_concurrent_subagents: int = Field(default=3, alias="MAX_CONCURRENT_SUBAGENTS")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


@lru_cache
def get_settings() -> AppSettings:
    """获取全局配置单例"""
    return AppSettings()
