from pydantic import BaseModel

from plugin_contracts.capability import CapabilitySummary


class InstallRequest(BaseModel):
    plugin_id: str
    version: str


class PluginActionRequest(BaseModel):
    plugin_id: str


class InstallationResponse(BaseModel):
    plugin_id: str
    version: str
    enabled: bool


class PublishResponse(BaseModel):
    plugin_id: str
    version: str
    checksum: str
    status: str


class CapabilityDiscoveryResponse(BaseModel):
    capabilities: list[CapabilitySummary]
