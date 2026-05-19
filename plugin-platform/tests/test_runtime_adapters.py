from pathlib import Path

import httpx
import pytest

from plugin_runtime_service.errors import CapabilityTypeError, RuntimeErrorResult
from plugin_runtime_service.openapi_adapter import OpenApiInvocation, invoke_openapi
from plugin_runtime_service.skill_context import execute_skill_context, load_skill_context
from plugin_runtime_service.streamable_mcp_adapter import McpJsonRpcRequest, call_streamable_mcp


def test_openapi_timeout_returns_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = invoke_openapi(
        OpenApiInvocation(method="GET", url="https://example.test/search", timeout_seconds=0.01),
        client=client,
    )

    assert isinstance(result, RuntimeErrorResult)
    assert result.error_code == "openapi_timeout"
    assert result.retryable


def test_streamable_mcp_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept"] == "application/json, text/event-stream"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_streamable_mcp(
        McpJsonRpcRequest(endpoint="https://example.test/mcp", method="tools/call"),
        client=client,
    )

    assert isinstance(result, dict)
    assert result["result"]["ok"] is True


def test_streamable_mcp_sse_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text='event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n',
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_streamable_mcp(
        McpJsonRpcRequest(endpoint="https://example.test/mcp", method="tools/call"),
        client=client,
    )

    assert isinstance(result, dict)
    assert result["events"] == ['{"jsonrpc":"2.0","id":1,"result":{"ok":true}}']


def test_skill_context_is_not_executable(example_plugin_dir: Path) -> None:
    context = load_skill_context(
        example_plugin_dir,
        "research-summary",
        "skills/research-summary.md",
    )

    assert "research documents" in context.content
    with pytest.raises(CapabilityTypeError):
        execute_skill_context(context)
