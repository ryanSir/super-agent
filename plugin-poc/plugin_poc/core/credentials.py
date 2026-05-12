from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..management.manager import PluginManagerError
from ..shared.io import dump_json, load_yaml


class CredentialError(PluginManagerError):
    """Raised when credential operations fail."""


def configure_credential(
    state_dir: str | Path,
    plugin_id: str,
    version: str,
    workspace: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    manifest, install_dir = _installed_manifest(state_dir, plugin_id, version)
    schema = _credential_schema(manifest, install_dir)
    fields = schema.get("fields", []) or []
    errors = _validate_required_fields(fields, values)
    if errors:
        raise CredentialError("; ".join(errors))

    stored_values = {
        field["name"]: _encode_value(values.get(field["name"]), field.get("type") == "secret") for field in fields
    }
    credentials = _load_credentials(state_dir)
    key = _credential_key(plugin_id, version, workspace)
    credentials["credentials"][key] = {
        "plugin_id": plugin_id,
        "version": version,
        "workspace": workspace,
        "auth_type": manifest.get("auth", {}).get("type", "none"),
        "values": stored_values,
        "configured_at": datetime.now(UTC).isoformat(),
    }
    _dump_credentials(state_dir, credentials)
    return redact_credential(credentials["credentials"][key])


def list_credentials(state_dir: str | Path) -> list[dict[str, Any]]:
    credentials = _load_credentials(state_dir)
    return [redact_credential(item) for item in credentials["credentials"].values()]


def has_credential(state_dir: str | Path, plugin_id: str, version: str, workspace: str) -> bool:
    credentials = _load_credentials(state_dir)
    return _credential_key(plugin_id, version, workspace) in credentials["credentials"]


def test_credential(state_dir: str | Path, plugin_id: str, version: str, workspace: str) -> dict[str, Any]:
    exists = has_credential(state_dir, plugin_id, version, workspace)
    return {
        "plugin_id": plugin_id,
        "version": version,
        "workspace": workspace,
        "ok": exists,
        "message": "credential exists" if exists else "credential is missing",
    }


def redact_credential(credential: dict[str, Any]) -> dict[str, Any]:
    values = {}
    for key, value in credential.get("values", {}).items():
        if isinstance(value, str) and value.startswith("POC:"):
            values[key] = "***"
        else:
            values[key] = value
    redacted = dict(credential)
    redacted["values"] = values
    return redacted


def plugin_requires_credential(manifest: dict[str, Any]) -> bool:
    return manifest.get("auth", {}).get("type", "none") != "none"


def _credential_schema(manifest: dict[str, Any], install_dir: Path) -> dict[str, Any]:
    schema_path = manifest.get("auth", {}).get("credential_schema")
    if not schema_path:
        return {"fields": []}
    data = load_yaml(install_dir / "source" / schema_path)
    return data if isinstance(data, dict) else {"fields": []}


def _installed_manifest(state_dir: str | Path, plugin_id: str, version: str) -> tuple[dict[str, Any], Path]:
    from ..management.manager import _installed_entry  # local import to avoid exposing internal helper as public API

    state = Path(state_dir).resolve()
    entry = _installed_entry(state, plugin_id, version)
    install_dir = Path(entry["install_dir"])
    manifest = load_yaml(install_dir / "manifest.yaml")
    if not isinstance(manifest, dict):
        raise CredentialError(f"invalid installed manifest for {plugin_id}@{version}")
    return manifest, install_dir


def _validate_required_fields(fields: list[dict[str, Any]], values: dict[str, Any]) -> list[str]:
    errors = []
    for field in fields:
        name = field.get("name")
        if field.get("required") and (name not in values or values.get(name) in (None, "")):
            errors.append(f"missing required credential field: {name}")
    return errors


def _encode_value(value: Any, secret: bool) -> Any:
    if not secret:
        return value
    raw = "" if value is None else str(value)
    return "POC:" + base64.b64encode(raw.encode("utf-8")).decode("ascii")


def _load_credentials(state_dir: str | Path) -> dict[str, Any]:
    path = Path(state_dir).resolve() / "credentials.json"
    if not path.exists():
        return {"credentials": {}}
    import json

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    data.setdefault("credentials", {})
    return data


def _dump_credentials(state_dir: str | Path, data: dict[str, Any]) -> None:
    dump_json(Path(state_dir).resolve() / "credentials.json", data)


def _credential_key(plugin_id: str, version: str, workspace: str) -> str:
    return f"{workspace}:{plugin_id}@{version}"
