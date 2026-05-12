from __future__ import annotations

import json
import shutil
from pathlib import Path

from plugin_poc.core.credentials import configure_credential
from plugin_poc.core.gateway import invoke_capability
from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.management.manager import enable_plugin, install_plugin
from plugin_poc.runtimes.mcp_runtime import _parse_response_body, list_mcp_tools

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "slack-demo"


def prepare_enabled_plugin(tmp_path: Path) -> Path:
    plugin_dir = tmp_path / "slack-demo"
    shutil.copytree(EXAMPLE, plugin_dir)
    registry_dir = tmp_path / "registry"
    state_dir = tmp_path / "state"
    publish_plugin(plugin_dir, registry_dir)
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")
    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")
    configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )
    return state_dir


def test_parse_sse_json_response() -> None:
    body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n'

    parsed = _parse_response_body(body, "text/event-stream")

    assert parsed["result"]["tools"] == []


def test_list_mcp_tools_with_mocked_jsonrpc(monkeypatch) -> None:
    def fake_jsonrpc(endpoint, method, params, request_id, timeout):
        assert endpoint == "https://example.com/mcp"
        assert method == "tools/list"
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [{"name": "demo_tool"}]}}

    monkeypatch.setattr("plugin_poc.runtimes.mcp_runtime._jsonrpc", fake_jsonrpc)

    assert list_mcp_tools("https://example.com/mcp") == [{"name": "demo_tool"}]


def test_invoke_mcp_capability_success(monkeypatch, tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    def fake_jsonrpc(endpoint, method, params, request_id, timeout):
        assert "stage-ai-fabric.zhihuiya.com" in endpoint
        assert method == "tools/call"
        assert params["name"] == "demo_tool"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": json.dumps({"ok": True})}]},
        }

    monkeypatch.setattr("plugin_poc.runtimes.mcp_runtime._jsonrpc", fake_jsonrpc)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.mcp.eureka-claw-mcp",
        {"tool_name": "demo_tool", "arguments": {"query": "EGFR"}},
        user="user_001",
    )

    assert result.success is True
    assert result.runtime == "streamable_http_mcp"
    assert result.output["tool_name"] == "demo_tool"


def test_invoke_mcp_missing_tool_name_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.mcp.eureka-claw-mcp",
        {"arguments": {}},
        user="user_001",
    )

    assert result.success is False
    assert result.error["code"] == "invalid_input"
