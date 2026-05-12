from __future__ import annotations

from pathlib import Path
from typing import Any

from ..shared.io import load_yaml


def invoke_openapi(
    capability: dict[str, Any],
    input_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    operation_id = input_data.get("operation_id")
    if not operation_id:
        return None, {"code": "invalid_input", "message": "operation_id is required"}

    operation = find_operation(capability, operation_id)
    if operation is None:
        return None, {"code": "operation_not_found", "message": f"operation_id not found: {operation_id}"}

    output = {
        "message": "mock openapi invocation succeeded",
        "operation_id": operation_id,
        "method": operation["method"].upper(),
        "path": operation["path"],
        "parameters": input_data.get("parameters", {}),
        "request_body": input_data.get("body"),
    }
    return output, None


def find_operation(capability: dict[str, Any], operation_id: str) -> dict[str, Any] | None:
    spec = _load_openapi_spec(capability)
    paths = spec.get("paths", {}) if isinstance(spec, dict) else {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            if operation.get("operationId") == operation_id:
                return {"path": path, "method": method, "operation": operation}
    return None


def _load_openapi_spec(capability: dict[str, Any]) -> dict[str, Any]:
    install_dir = Path(capability["install_dir"])
    source = capability["source"]
    data = load_yaml(install_dir / "source" / source)
    return data if isinstance(data, dict) else {}
