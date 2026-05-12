from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..shared.errors import PluginPocError


class MCPRuntimeError(PluginPocError):
    """Raised when Streamable HTTP MCP calls fail."""


def list_mcp_tools(endpoint: str, timeout: float = 20.0) -> list[dict[str, Any]]:
    response = _jsonrpc(endpoint, "tools/list", {}, request_id=1, timeout=timeout)
    result = response.get("result", {})
    tools = result.get("tools", [])
    return tools if isinstance(tools, list) else []


def call_mcp_tool(
    endpoint: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    response = _jsonrpc(
        endpoint,
        "tools/call",
        {"name": tool_name, "arguments": arguments},
        request_id=2,
        timeout=timeout,
    )
    return response.get("result", {})


def invoke_mcp(
    capability: dict[str, Any],
    input_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    endpoint = capability.get("endpoint")
    if not endpoint:
        return None, {"code": "invalid_mcp_endpoint", "message": "mcp endpoint is missing"}

    tool_name = input_data.get("tool_name")
    if not tool_name:
        return None, {"code": "invalid_input", "message": "tool_name is required"}

    arguments = input_data.get("arguments", {})
    if not isinstance(arguments, dict):
        return None, {"code": "invalid_input", "message": "arguments must be an object"}

    try:
        result = call_mcp_tool(endpoint, tool_name, arguments)
    except MCPRuntimeError as exc:
        return None, {"code": "mcp_request_failed", "message": str(exc)}

    return {
        "message": "mcp tool invocation succeeded",
        "tool_name": tool_name,
        "result": result,
    }, None


def _jsonrpc(
    endpoint: str,
    method: str,
    params: dict[str, Any],
    request_id: int,
    timeout: float,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided POC endpoint
            body = response.read().decode("utf-8")
            content_type = response.headers.get("content-type", "")
    except urllib.error.URLError as exc:
        raise MCPRuntimeError(f"request failed: {exc}") from exc

    data = _parse_response_body(body, content_type)
    if "error" in data:
        raise MCPRuntimeError(json.dumps(data["error"], ensure_ascii=False))
    return data


def _parse_response_body(body: str, content_type: str) -> dict[str, Any]:
    if "text/event-stream" in content_type:
        return _parse_sse_json(body)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MCPRuntimeError(f"invalid JSON response: {body[:200]}") from exc
    if not isinstance(data, dict):
        raise MCPRuntimeError("JSON-RPC response must be an object")
    return data


def _parse_sse_json(body: str) -> dict[str, Any]:
    data_lines = []
    for line in body.splitlines():
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
    if not data_lines:
        raise MCPRuntimeError("SSE response did not include data lines")
    raw = "\n".join(data_lines)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MCPRuntimeError(f"invalid SSE JSON data: {raw[:200]}") from exc
    if not isinstance(data, dict):
        raise MCPRuntimeError("SSE JSON-RPC response must be an object")
    return data
