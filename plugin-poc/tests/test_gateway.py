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
    return state_dir


def configure_demo_credential(state_dir: Path) -> None:
    configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )


def test_invoke_tool_capability_success(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_demo_credential(state_dir)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello"},
        confirm_sensitive=True,
    )

    assert result.success is True
    assert result.runtime == "local_mock_tool"
    assert result.output["tool"] == "send_message"


def test_invoke_missing_required_input_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_demo_credential(state_dir)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001"},
        confirm_sensitive=True,
    )

    assert result.success is False
    assert result.error["code"] == "invalid_input"
    assert result.error["details"]["missing"] == ["text"]


def test_invoke_missing_capability_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(state_dir, "ws_001", "agent_001", "company.slack-demo.tool.missing", {})

    assert result.success is False
    assert result.error["code"] == "capability_not_found"


def test_invoke_unsupported_capability_type_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_demo_credential(state_dir)

    result = invoke_capability(state_dir, "ws_001", "agent_001", "company.slack-demo.skill.summarize-channel", {})

    assert result.success is False
    assert result.error["code"] == "unsupported_capability_type"


def test_cli_invoke_success(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_demo_credential(state_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "invoke",
            "company.slack-demo.tool.send_message",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
            "--confirm-sensitive",
            "--input",
            '{"channel_id":"C001","text":"hello"}',
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"success": true' in result.stdout


def test_cli_invoke_invalid_json_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "invoke",
            "company.slack-demo.tool.send_message",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
            "--input",
            "{bad-json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "invalid JSON input" in result.stderr
