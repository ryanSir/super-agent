from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from plugin_poc.core.credentials import configure_credential
from plugin_poc.core.gateway import invoke_capability
from plugin_poc.core.observability import list_runtime_events
from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.management.manager import enable_plugin, install_plugin, list_capabilities
from plugin_poc.runtime_host import runtime_health, start_runtime, stop_runtime
from plugin_poc.runtimes.data_source_runtime import list_data_sources

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


def test_data_source_invocation_through_gateway(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.datasource.slack_messages",
        {"query": "mcp", "limit": 1},
        user="user_001",
    )

    assert result.success is True
    assert result.runtime == "local_data_source"
    assert result.output["total"] == 1
    assert "MCP streamable endpoint" in result.output["items"][0]["text"]


def test_list_data_sources(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    sources = list_data_sources(state_dir, "ws_001", "agent_001")

    assert [source["capability_id"] for source in sources] == ["company.slack-demo.datasource.slack_messages"]


def test_runtime_host_registers_stdio_adapter(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    runtime = start_runtime(state_dir, "company.slack-demo", "1.0.0")

    assert runtime["status"] == "running"
    assert runtime["adapters"] == [
        {
            "name": "local-stdio-demo",
            "transport": "stdio",
            "command": "python -m plugin_poc.demo_stdio_mcp",
            "adapter_endpoint": "http://127.0.0.1:8790/mcp/company.slack-demo/local-stdio-demo",
            "status": "registered",
        }
    ]
    assert runtime_health(state_dir, "company.slack-demo", "1.0.0")["status"] == "ok"
    assert stop_runtime(state_dir, "company.slack-demo", "1.0.0")["status"] == "stopped"


def test_observability_records_success_and_timeout(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    success = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.datasource.slack_messages",
        {"query": "plugin"},
        user="user_001",
    )
    timeout = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello", "simulate_delay_ms": 500},
        user="user_001",
        confirm_sensitive=True,
        timeout_ms=100,
    )

    assert success.success is True
    assert timeout.success is False
    assert timeout.error["code"] == "runtime_timeout"
    events = list_runtime_events(state_dir)
    assert [event["success"] for event in events] == [True, False]
    assert events[-1]["error_code"] == "runtime_timeout"


def test_capability_index_contains_stdio_mcp_capability(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    ids = {capability["capability_id"] for capability in list_capabilities(state_dir, "ws_001", "agent_001")}

    assert "company.slack-demo.mcp.local-stdio-demo" in ids


def test_cli_run_e2e(tmp_path: Path) -> None:
    env = {"PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "run-e2e",
            "--plugin-dir",
            str(EXAMPLE),
            "--registry",
            str(tmp_path / "registry"),
            "--state",
            str(tmp_path / "state"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"status": "ok"' in result.stdout
    assert "company.slack-demo.tool.send_message" in result.stdout
