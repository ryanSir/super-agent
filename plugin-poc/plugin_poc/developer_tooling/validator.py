from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..shared.errors import ValidationError
from ..shared.io import load_yaml
from ..shared.models import Manifest, ValidationResult

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*[a-z0-9]$")

VALID_AUTH_TYPES = {"none", "api_key", "bearer_token", "oauth2"}
VALID_RUNTIME_MODES = {"none", "remote", "local_daemon", "sidecar", "container", "serverless"}
VALID_MCP_TRANSPORTS = {"streamable_http", "stdio", "http_sse"}


def validate_plugin(plugin_dir: str | Path) -> ValidationResult:
    root = Path(plugin_dir).resolve()
    errors: list[str] = []

    if not root.exists() or not root.is_dir():
        raise ValidationError([f"plugin directory does not exist: {root}"])

    manifest_path = root / "plugin.yaml"
    if not manifest_path.exists():
        raise ValidationError([f"missing manifest: {manifest_path}"])

    try:
        manifest = load_yaml(manifest_path)
    except Exception as exc:  # noqa: BLE001 - surfaced as validation error for CLI users
        raise ValidationError([f"failed to parse plugin.yaml: {exc}"]) from exc

    if not isinstance(manifest, dict):
        raise ValidationError(["plugin.yaml must be a mapping/object"])

    referenced_files: list[Path] = []
    _validate_identity(manifest, errors)
    _validate_capabilities(root, manifest, errors, referenced_files)
    _validate_auth(root, manifest, errors, referenced_files)
    _validate_permissions(manifest, errors)
    _validate_runtime(manifest, errors)

    if errors:
        raise ValidationError(errors)

    unique_files = tuple(sorted(set(referenced_files)))
    return ValidationResult(
        plugin_dir=root,
        manifest_path=manifest_path,
        manifest=manifest,
        referenced_files=unique_files,
    )


def _validate_identity(manifest: Manifest, errors: list[str]) -> None:
    required = ["schema_version", "id", "name", "version", "capabilities"]
    for field in required:
        if field not in manifest:
            errors.append(f"missing required field: {field}")

    plugin_id = manifest.get("id")
    if plugin_id is not None and (not isinstance(plugin_id, str) or not PLUGIN_ID_PATTERN.match(plugin_id)):
        errors.append("id must use lowercase letters, numbers, dots, underscores or hyphens")

    version = manifest.get("version")
    if version is not None and (not isinstance(version, str) or not SEMVER_PATTERN.match(version)):
        errors.append("version must use semantic version format MAJOR.MINOR.PATCH")

    name = manifest.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        errors.append("name must be a non-empty string")


def _validate_capabilities(root: Path, manifest: Manifest, errors: list[str], referenced_files: list[Path]) -> None:
    capabilities = manifest.get("capabilities")
    if capabilities is None:
        return
    if not isinstance(capabilities, dict):
        errors.append("capabilities must be a mapping/object")
        return

    if not any(capabilities.get(key) for key in ("tools", "skills", "mcp", "openapi", "data_sources")):
        errors.append("capabilities must define at least one of tools, skills, mcp, openapi, data_sources")

    _validate_path_list(root, capabilities, "tools", "path", errors, referenced_files)
    _validate_path_list(root, capabilities, "skills", "path", errors, referenced_files)
    _validate_path_list(root, capabilities, "data_sources", "path", errors, referenced_files)
    _validate_openapi(root, capabilities, errors, referenced_files)
    _validate_mcp(capabilities, errors)


def _validate_path_list(
    root: Path,
    owner: dict[str, Any],
    list_key: str,
    path_key: str,
    errors: list[str],
    referenced_files: list[Path],
) -> None:
    entries = owner.get(list_key, [])
    if entries in (None, []):
        return
    if not isinstance(entries, list):
        errors.append(f"capabilities.{list_key} must be a list")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"capabilities.{list_key}[{index}] must be an object")
            continue
        _record_existing_path(
            root,
            entry,
            path_key,
            f"capabilities.{list_key}[{index}].{path_key}",
            errors,
            referenced_files,
        )


def _validate_openapi(
    root: Path,
    capabilities: dict[str, Any],
    errors: list[str],
    referenced_files: list[Path],
) -> None:
    entries = capabilities.get("openapi", [])
    if entries in (None, []):
        return
    if not isinstance(entries, list):
        errors.append("capabilities.openapi must be a list")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"capabilities.openapi[{index}] must be an object")
            continue
        if not entry.get("name"):
            errors.append(f"capabilities.openapi[{index}].name is required")
        _record_existing_path(root, entry, "spec", f"capabilities.openapi[{index}].spec", errors, referenced_files)


def _validate_mcp(capabilities: dict[str, Any], errors: list[str]) -> None:
    entries = capabilities.get("mcp", [])
    if entries in (None, []):
        return
    if not isinstance(entries, list):
        errors.append("capabilities.mcp must be a list")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"capabilities.mcp[{index}] must be an object")
            continue
        transport = entry.get("transport")
        if transport not in VALID_MCP_TRANSPORTS:
            errors.append(f"capabilities.mcp[{index}].transport must be one of {sorted(VALID_MCP_TRANSPORTS)}")
        if transport == "streamable_http" and not entry.get("url"):
            errors.append(f"capabilities.mcp[{index}].url is required for streamable_http")
        if transport == "stdio" and not entry.get("command"):
            errors.append(f"capabilities.mcp[{index}].command is required for stdio")


def _validate_auth(root: Path, manifest: Manifest, errors: list[str], referenced_files: list[Path]) -> None:
    auth = manifest.get("auth")
    if auth is None:
        return
    if not isinstance(auth, dict):
        errors.append("auth must be an object")
        return
    auth_type = auth.get("type", "none")
    if auth_type not in VALID_AUTH_TYPES:
        errors.append(f"auth.type must be one of {sorted(VALID_AUTH_TYPES)}")
    if "credential_schema" in auth:
        _record_existing_path(root, auth, "credential_schema", "auth.credential_schema", errors, referenced_files)


def _validate_permissions(manifest: Manifest, errors: list[str]) -> None:
    permissions = manifest.get("permissions", {})
    if permissions in (None, {}):
        return
    if not isinstance(permissions, dict):
        errors.append("permissions must be an object")
        return
    for key in ("read", "write", "sensitive_actions"):
        if key in permissions and not isinstance(permissions[key], list):
            errors.append(f"permissions.{key} must be a list")


def _validate_runtime(manifest: Manifest, errors: list[str]) -> None:
    runtime = manifest.get("runtime", {"mode": "none"})
    if runtime is None:
        return
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
        return
    mode = runtime.get("mode", "none")
    if mode not in VALID_RUNTIME_MODES:
        errors.append(f"runtime.mode must be one of {sorted(VALID_RUNTIME_MODES)}")


def _record_existing_path(
    root: Path,
    entry: dict[str, Any],
    key: str,
    field_name: str,
    errors: list[str],
    referenced_files: list[Path],
) -> None:
    value = entry.get(key)
    if not value or not isinstance(value, str):
        errors.append(f"{field_name} is required")
        return
    path = root / value
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{field_name} must stay inside plugin directory: {value}")
        return
    if not resolved.exists() or not resolved.is_file():
        errors.append(f"{field_name} points to missing file: {value}")
        return
    referenced_files.append(resolved)
