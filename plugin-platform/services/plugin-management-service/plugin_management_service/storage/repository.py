from typing import Protocol

from pydantic import BaseModel, Field

from plugin_contracts.capability import CapabilitySummary
from plugin_contracts.manifest import PluginManifest


class PluginVersionRecord(BaseModel):
    plugin_id: str
    version: str
    checksum: str
    manifest: PluginManifest
    capabilities: list[CapabilitySummary] = Field(default_factory=list)
    package_path: str
    status: str = "published"
    created_at: str


class InstallationRecord(BaseModel):
    workspace_id: str
    plugin_id: str
    version: str
    enabled: bool = False
    agent_ids: list[str] = Field(default_factory=list)


class RegistryRepository(Protocol):
    def save_version(self, record: PluginVersionRecord) -> PluginVersionRecord: ...

    def get_version(self, plugin_id: str, version: str) -> PluginVersionRecord | None: ...

    def list_versions(self) -> list[PluginVersionRecord]: ...


class ManagerRepository(Protocol):
    def save_installation(self, record: InstallationRecord) -> InstallationRecord: ...

    def get_installation(
        self,
        workspace_id: str,
        plugin_id: str,
    ) -> InstallationRecord | None: ...

    def list_installations(self, workspace_id: str) -> list[InstallationRecord]: ...
