"""Pydantic Settings 多环境配置管理

从 .env 文件加载配置，按功能域分组管理。
"""

# 标准库
from functools import lru_cache
from typing import Optional

# 第三方库
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """应用基础配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用配置
    app_name: str = "super-agent"
    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_port: int = 9000
    secret_key: str = Field(default="dev-secret-key", alias="APP_SECRET_KEY")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_engine: str = "django.db.backends.postgresql"
    db_name: str = Field(default="core_eureka_qa", alias="DB_NAME")
    db_user: str = Field(default="analytics", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class RedisSettings(BaseSettings):
    """Redis 配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=100, alias="REDIS_MAX_CONNECTIONS")
    redis_cluster_mode: bool = Field(default=False, alias="REDIS_CLUSTER_MODE")

    @property
    def url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class LLMSettings(BaseSettings):
    """LLM 配置（通过 LiteLLM 路由）"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_api_base: str = Field(default="", alias="OPENAI_API_BASE")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field(default="", alias="ANTHROPIC_BASE_URL")
    anthropic_claude_model: str = Field(default="claude-sonnet-4-5-20250929", alias="ANTHROPIC_CLAUDE_MODEL")

    claude_model: str = Field(default="claude-4.5-sonnet", alias="CLAUDE_MODEL")

    # 模型别名映射（不同场景使用不同模型）
    planning_model: str = Field(default="claude-4.5-sonnet", alias="PLANNING_MODEL")
    execution_model: str = Field(default="claude-4.5-sonnet", alias="EXECUTION_MODEL")
    fast_model: str = Field(default="gpt-4o-mini", alias="FAST_MODEL")


class E2BSettings(BaseSettings):
    """E2B 沙箱配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sandbox_provider: str = Field(default="tencent", alias="SANDBOX_PROVIDER")
    e2b_api_key: str = Field(default="", alias="E2B_API_KEY")
    e2b_template: str = Field(default="custom-sandbox-1", alias="E2B_TEMPLATE")
    e2b_timeout: int = Field(default=300, alias="E2B_TIMEOUT")
    e2b_work_dir: str = Field(default="/data/e2b/workspace", alias="E2B_WORK_DIR")
    e2b_scripts_dir: str = Field(default="/data/e2b/scripts", alias="E2B_SCRIPTS_DIR")
    e2b_domain: str = Field(default="ap-beijing.tencentags.com", alias="E2B_DOMAIN")
    use_e2b: bool = Field(default=True, alias="USE_E2B")
    sandbox_pi_provider: str = Field(default="my-gateway", alias="SANDBOX_PI_PROVIDER")
    sandbox_pi_model: str = Field(default="gpt-4o", alias="SANDBOX_PI_MODEL")


class LangfuseSettings(BaseSettings):
    """Langfuse 监控配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_base_url: str = Field(default="", alias="LANGFUSE_BASE_URL")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")

    @property
    def is_configured(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


class TemporalSettings(BaseSettings):
    """Temporal 工作流配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    temporal_host: str = Field(default="localhost:7233", alias="TEMPORAL_HOST")
    temporal_namespace: str = Field(default="default", alias="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(default="super-agent-queue", alias="TEMPORAL_TASK_QUEUE")


class MCPSettings(BaseSettings):
    """MCP 工具服务配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mcp_server_url: str = Field(
        default="",
        alias="MCP_SERVER_URL",
    )
    mcp_servers: str = Field(
        default="",
        alias="MCP_SERVERS",
        description="JSON 数组，格式：[{\"name\":\"x\",\"url\":\"...\",\"headers\":{}}]",
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.mcp_server_url or self.mcp_servers)


class MiddlewareSettings(BaseSettings):
    """Agent Middleware 配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=True, alias="MIDDLEWARE_ENABLED")
    loop_warn_threshold: int = Field(default=3, alias="MIDDLEWARE_LOOP_WARN_THRESHOLD")
    loop_hard_limit: int = Field(default=5, alias="MIDDLEWARE_LOOP_HARD_LIMIT")
    loop_window_size: int = Field(default=20, alias="MIDDLEWARE_LOOP_WINDOW_SIZE")
    summarization_threshold_ratio: float = Field(
        default=0.7, alias="MIDDLEWARE_SUMMARIZATION_THRESHOLD_RATIO"
    )


class MemorySettings(BaseSettings):
    """跨会话记忆配置"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    max_facts: int = Field(default=100, alias="MEMORY_MAX_FACTS")
    debounce_seconds: float = Field(default=5.0, alias="MEMORY_DEBOUNCE_SECONDS")
    update_model: str = Field(default="fast", alias="MEMORY_UPDATE_MODEL")
    redis_key_prefix: str = Field(default="memory", alias="MEMORY_REDIS_KEY_PREFIX")


class Settings(BaseSettings):
    """聚合配置入口"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    middleware: MiddlewareSettings = Field(default_factory=MiddlewareSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
