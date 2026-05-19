from typing import Any

import httpx
from pydantic import BaseModel

from plugin_runtime_service.errors import RuntimeErrorResult


class McpJsonRpcRequest(BaseModel):
    endpoint: str
    method: str
    params: dict[str, Any] = {}
    request_id: str | int = 1
    protocol_version: str = "2025-06-18"
    session_id: str | None = None
    timeout_seconds: float = 10.0


def call_streamable_mcp(
    request: McpJsonRpcRequest,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any] | RuntimeErrorResult:
    owns_client = client is None
    http_client = client or httpx.Client()
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": request.protocol_version,
    }
    if request.session_id:
        headers["Mcp-Session-Id"] = request.session_id

    body = {
        "jsonrpc": "2.0",
        "id": request.request_id,
        "method": request.method,
        "params": request.params,
    }

    try:
        response = http_client.post(
            request.endpoint,
            headers=headers,
            json=body,
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            return response.json()
        if content_type.startswith("text/event-stream"):
            return {"events": _parse_sse_json_messages(response.text)}
        return RuntimeErrorResult(
            error_code="mcp_unsupported_content_type",
            message=f"Unsupported MCP response content type: {content_type}",
        )
    except httpx.TimeoutException:
        return RuntimeErrorResult(
            error_code="mcp_timeout",
            message=f"MCP invocation timed out after {request.timeout_seconds}s",
            retryable=True,
        )
    except httpx.HTTPError as exc:
        return RuntimeErrorResult(
            error_code="mcp_http_error",
            message=str(exc),
            retryable=False,
        )
    finally:
        if owns_client:
            http_client.close()


def _parse_sse_json_messages(text: str) -> list[str]:
    messages: list[str] = []
    for line in text.splitlines():
        if line.startswith("data:"):
            messages.append(line.removeprefix("data:").strip())
    return messages
