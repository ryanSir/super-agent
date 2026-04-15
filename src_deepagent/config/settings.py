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
    orchestrator_model: str = Field(default="claude-4.5-sonnet", alias="ORCHESTRATOR_MODEL")
    subagent_model: str = Field(default="gpt-4o-mini", alias="SUBAGENT_MODEL")
    classifier_model: str = Field(default="gpt-4o-mini", alias="CLASSIFIER_MODEL")
    request_timeout: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT")
    enable_litellm: bool = Field(default=False, alias="ENABLE_LITELLM")
    baidu_api_key: str = Field(default="", alias="BAIDU_API_KEY")

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
    conversation_max_turns: int = Field(default=20, alias="MEMORY_CONVERSATION_MAX_TURNS")
    conversation_ttl: int = Field(default=3600, alias="MEMORY_CONVERSATION_TTL")

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class MCPSettings(BaseSettings):
    """MCP 工具服务配置"""

    servers_json: str = Field(default="", alias="MCP_SERVERS")
    server_url: str = Field(default="", alias="MCP_SERVER_URL")
    connect_timeout: float = Field(default=10.0, alias="MCP_CONNECT_TIMEOUT")
    refresh_interval: int = Field(default=300, alias="MCP_REFRESH_INTERVAL")  # 秒，0 表示不刷新

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


class ReasoningSettings(BaseSettings):
    """推理引擎配置"""

    # LLM 主分类超时
    llm_classify_timeout: float = Field(default=15.0, alias="REASONING_LLM_CLASSIFY_TIMEOUT")

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
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)

    model_config = {"env_prefix": "", "extra": "ignore", "env_file": ".env"}


@lru_cache
def get_settings() -> AppSettings:
    """获取全局配置单例"""
    return AppSettings()
