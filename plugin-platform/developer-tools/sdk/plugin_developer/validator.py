from pathlib import Path

from pydantic import ValidationError

from plugin_contracts.capability import (
    CapabilitySummary,
    CapabilityType,
    ValidationIssue,
    ValidationResult,
)
from plugin_contracts.manifest import PluginManifest, load_manifest


def validate_plugin(plugin_dir: Path) -> ValidationResult:
    issues: list[ValidationIssue] = []
    manifest_path = plugin_dir / "plugin.yaml"
    if not manifest_path.exists():
        return ValidationResult(
            valid=False,
            issues=[
                ValidationIssue(
                    code="manifest_missing",
                    message="plugin.yaml is required",
                    path="plugin.yaml",
                )
            ],
        )

    try:
        manifest = load_manifest(plugin_dir)
    except (ValidationError, ValueError) as exc:
        return ValidationResult(
            valid=False,
            issues=[
                ValidationIssue(
                    code="manifest_invalid",
                    message=str(exc),
                    path="plugin.yaml",
                )
            ],
        )

    issues.extend(_validate_referenced_files(plugin_dir, manifest))
    issues.extend(_validate_mcp_transports(manifest))

    return ValidationResult(
        valid=not any(issue.severity == "error" for issue in issues),
        plugin_id=manifest.plugin.id,
        version=manifest.plugin.version,
        capabilities=_build_capability_summary(manifest),
        issues=issues,
    )


def _validate_referenced_files(plugin_dir: Path, manifest: PluginManifest) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    refs = [
        *[(cap.path, f"capabilities.{cap.name}") for cap in manifest.capabilities],
        *[(mcp.path, f"mcp_servers.{mcp.name}") for mcp in manifest.mcp_servers],
        *[(credential.path, f"credentials.{credential.name}") for credential in manifest.credentials],
        *[(asset_path, "assets") for asset_path in manifest.assets],
    ]
    for relative_path, field_path in refs:
        if not (plugin_dir / relative_path).exists():
            issues.append(
                ValidationIssue(
                    code="referenced_file_missing",
                    message=f"Referenced file does not exist: {relative_path}",
                    path=field_path,
                )
            )
    return issues


def _validate_mcp_transports(manifest: PluginManifest) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for server in manifest.mcp_servers:
        if server.transport != "streamable-http":
            issues.append(
                ValidationIssue(
                    code="unsupported_mcp_transport",
                    message="Only Streamable HTTP MCP is supported in phase one",
                    path=f"mcp_servers.{server.name}.transport",
                )
            )
    return issues


def _build_capability_summary(manifest: PluginManifest) -> list[CapabilitySummary]:
    summaries = [
        CapabilitySummary(
            plugin_id=manifest.plugin.id,
            plugin_version=manifest.plugin.version,
            type=cap.type,
            name=cap.name,
            description=cap.description,
            invocation={"path": cap.path},
        )
        for cap in manifest.capabilities
    ]
    summaries.extend(
        CapabilitySummary(
            plugin_id=manifest.plugin.id,
            plugin_version=manifest.plugin.version,
            type=CapabilityType.MCP,
            name=server.name,
            description=server.description,
            invocation={
                "transport": server.transport,
                "endpoint": getattr(server, "endpoint", None),
                "path": server.path,
            },
        )
        for server in manifest.mcp_servers
    )
    return summaries
