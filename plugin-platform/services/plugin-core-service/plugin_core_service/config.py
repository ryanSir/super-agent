from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PluginPlatformSettings(BaseSettings):
    """Backend settings for local development and future deployment wiring."""

    model_config = SettingsConfigDict(env_prefix="PLUGIN_PLATFORM_", extra="ignore")

    data_dir: Path = Field(default=Path(".plugin-platform-data"))
    registry_dir: Path | None = None
    package_dir: Path | None = None
    default_publish_timeout_seconds: float = 10.0

    @property
    def resolved_registry_dir(self) -> Path:
        return self.registry_dir or self.data_dir / "registry"

    @property
    def resolved_package_dir(self) -> Path:
        return self.package_dir or self.data_dir / "packages"


def get_settings() -> PluginPlatformSettings:
    return PluginPlatformSettings()
