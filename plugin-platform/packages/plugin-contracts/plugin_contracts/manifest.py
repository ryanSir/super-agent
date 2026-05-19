from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from plugin_contracts.capability import CapabilityRef


class PluginMetadata(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str
    version: str
    publisher: str
    description: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    tags: list[str] = Field(default_factory=list)


class CredentialRef(BaseModel):
    name: str
    path: str
    required: bool = True


class StreamableMcpConfig(BaseModel):
    name: str
    path: str
    transport: Literal["streamable-http"]
    endpoint: str
    description: str | None = None


class UnsupportedMcpConfig(BaseModel):
    name: str
    path: str
    transport: str
    endpoint: str | None = None
    command: str | None = None
    description: str | None = None


class PluginManifest(BaseModel):
    schema_version: str = "0.1"
    plugin: PluginMetadata
    capabilities: list[CapabilityRef] = Field(default_factory=list)
    mcp_servers: list[StreamableMcpConfig | UnsupportedMcpConfig] = Field(default_factory=list)
    credentials: list[CredentialRef] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != "0.1":
            raise ValueError("only plugin schema_version 0.1 is supported")
        return value


def load_manifest(plugin_dir: Path) -> PluginManifest:
    manifest_path = plugin_dir / "plugin.yaml"
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return PluginManifest.model_validate(data)
