from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CapabilityType(StrEnum):
    SKILL = "skill"
    OPENAPI = "openapi"
    MCP = "mcp"


class CapabilityRef(BaseModel):
    type: CapabilityType
    name: str
    path: str
    description: str | None = None


class CapabilitySummary(BaseModel):
    plugin_id: str
    plugin_version: str
    type: CapabilityType
    name: str
    description: str | None = None
    invocation: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    code: str
    message: str
    path: str | None = None
    severity: Literal["error", "warning"] = "error"


class ValidationResult(BaseModel):
    valid: bool
    plugin_id: str | None = None
    version: str | None = None
    capabilities: list[CapabilitySummary] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
