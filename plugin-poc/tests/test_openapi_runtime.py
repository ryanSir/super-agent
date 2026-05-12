from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from plugin_poc.core.credentials import configure_credential
from plugin_poc.core.gateway import invoke_capability
from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.management.manager import enable_plugin, install_plugin

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


def test_invoke_openapi_operation_success(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.openapi.slack-demo-api",
        {"operation_id": "listMessages", "parameters": {"limit": 10}},
        user="user_001",
    )

    assert result.success is True
    assert result.runtime == "mock_openapi"
    assert result.output["method"] == "GET"
    assert result.output["path"] == "/messages"


def test_invoke_openapi_missing_operation_id_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.openapi.slack-demo-api",
        {},
        user="user_001",
    )

    assert result.success is False
    assert result.error["code"] == "invalid_input"


def test_invoke_openapi_unknown_operation_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.openapi.slack-demo-api",
        {"operation_id": "missingOperation"},
        user="user_001",
    )

    assert result.success is False
    assert result.error["code"] == "operation_not_found"


def test_cli_invoke_openapi_success(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "invoke",
            "company.slack-demo.openapi.slack-demo-api",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
            "--user",
            "user_001",
            "--input",
            '{"operation_id":"listMessages","parameters":{"limit":10}}',
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"runtime": "mock_openapi"' in result.stdout
