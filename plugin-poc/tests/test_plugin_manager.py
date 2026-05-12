from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.management.manager import (
    PluginManagerError,
    disable_plugin,
    enable_plugin,
    install_plugin,
    list_capabilities,
    list_installed,
    uninstall_plugin,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "slack-demo"


def copy_example(tmp_path: Path) -> Path:
    target = tmp_path / "slack-demo"
    shutil.copytree(EXAMPLE, target)
    return target


def publish_example(tmp_path: Path) -> tuple[Path, Path]:
    plugin_dir = copy_example(tmp_path)
    registry_dir = tmp_path / "registry"
    publish_plugin(plugin_dir, registry_dir)
    return plugin_dir, registry_dir


def test_install_plugin_from_registry(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)
    state_dir = tmp_path / "state"

    installed = install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")

    assert installed["plugin_id"] == "company.slack-demo"
    assert (state_dir / "installed_plugins.json").exists()
    assert (state_dir / "installed" / "company.slack-demo" / "1.0.0" / "source" / "plugin.yaml").exists()
    assert len(list_installed(state_dir)) == 1


def test_install_missing_plugin_fails(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)

    with pytest.raises(PluginManagerError):
        install_plugin(registry_dir, tmp_path / "state", "company.missing", "1.0.0")


def test_enable_plugin_builds_capability_index(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)
    state_dir = tmp_path / "state"
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")

    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")
    capabilities = list_capabilities(state_dir, "ws_001", "agent_001")

    capability_ids = {item["capability_id"] for item in capabilities}
    assert "company.slack-demo.tool.send_message" in capability_ids
    assert "company.slack-demo.skill.summarize-channel" in capability_ids
    assert "company.slack-demo.openapi.slack-demo-api" in capability_ids
    assert "company.slack-demo.datasource.slack_messages" in capability_ids
    assert "company.slack-demo.mcp.eureka-claw-mcp" in capability_ids


def test_capabilities_are_scoped_by_agent(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)
    state_dir = tmp_path / "state"
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")
    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")

    assert list_capabilities(state_dir, "ws_001", "agent_002") == []


def test_disable_plugin_removes_capabilities(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)
    state_dir = tmp_path / "state"
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")
    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")

    disable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")

    assert list_capabilities(state_dir, "ws_001", "agent_001") == []


def test_uninstall_plugin_removes_state(tmp_path: Path) -> None:
    _, registry_dir = publish_example(tmp_path)
    state_dir = tmp_path / "state"
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")
    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")

    uninstall_plugin(state_dir, "company.slack-demo", "1.0.0")

    assert list_installed(state_dir) == []
    assert list_capabilities(state_dir, "ws_001", "agent_001") == []
    assert not (state_dir / "installed" / "company.slack-demo" / "1.0.0").exists()


def test_cli_install_enable_list_capabilities(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    registry_dir = tmp_path / "registry"
    state_dir = tmp_path / "state"
    env = {"PYTHONPATH": str(ROOT)}

    commands = [
        [
            "publish",
            str(plugin_dir),
            "--registry",
            str(registry_dir),
            "--force",
        ],
        [
            "install",
            "company.slack-demo",
            "--version",
            "1.0.0",
            "--registry",
            str(registry_dir),
            "--state",
            str(state_dir),
        ],
        [
            "enable",
            "company.slack-demo",
            "--version",
            "1.0.0",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
        ],
        [
            "list-capabilities",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
        ],
    ]

    output = ""
    for command in commands:
        result = subprocess.run(
            [sys.executable, "-m", "plugin_poc.cli", *command],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        output = result.stdout

    assert "company.slack-demo.tool.send_message" in output
