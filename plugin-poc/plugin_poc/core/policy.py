from __future__ import annotations

from pathlib import Path
from typing import Any

from ..shared.io import load_yaml
from .credentials import has_credential, plugin_requires_credential


def check_invocation_policy(
    state_dir: str | Path,
    capability: dict[str, Any],
    confirm_sensitive: bool,
) -> dict[str, Any] | None:
    manifest = _capability_manifest(capability)
    plugin_id = capability["plugin_id"]
    version = capability["version"]
    workspace = capability["workspace"]

    if plugin_requires_credential(manifest) and not has_credential(state_dir, plugin_id, version, workspace):
        return {
            "code": "missing_credential",
            "message": f"credential is required for {plugin_id}@{version} in workspace {workspace}",
        }

    sensitive_actions = manifest.get("permissions", {}).get("sensitive_actions", []) or []
    if capability.get("name") in sensitive_actions and not confirm_sensitive:
        return {
            "code": "sensitive_action_requires_confirmation",
            "message": f"tool {capability.get('name')} requires explicit confirmation",
        }

    return None


def _capability_manifest(capability: dict[str, Any]) -> dict[str, Any]:
    install_dir = Path(capability["install_dir"])
    manifest = load_yaml(install_dir / "manifest.yaml")
    return manifest if isinstance(manifest, dict) else {}
