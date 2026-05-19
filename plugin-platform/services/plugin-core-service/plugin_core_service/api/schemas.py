from pydantic import BaseModel

from plugin_contracts.capability import CapabilitySummary


class InstallRequest(BaseModel):
    workspace_id: str
    plugin_id: str
    version: str


class PluginActionRequest(BaseModel):
    workspace_id: str
    plugin_id: str


class BindAgentRequest(BaseModel):
    workspace_id: str
    plugin_id: str
    agent_id: str


class InstallationResponse(BaseModel):
    workspace_id: str
    plugin_id: str
    version: str
    enabled: bool
    agent_ids: list[str]


class PublishResponse(BaseModel):
    plugin_id: str
    version: str
    checksum: str
    status: str


class CapabilityDiscoveryResponse(BaseModel):
    workspace_id: str
    agent_id: str | None = None
    capabilities: list[CapabilitySummary]
