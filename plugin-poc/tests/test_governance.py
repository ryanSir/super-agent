from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from plugin_poc.core.audit import list_audit_records
from plugin_poc.core.credentials import CredentialError, configure_credential, list_credentials
from plugin_poc.core.credentials import test_credential as check_credential
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


def test_configure_credential_redacts_secret(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    credential = configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )

    assert credential["values"]["client_id"] == "demo-client"
    assert credential["values"]["client_secret"] == "***"
    assert list_credentials(state_dir)[0]["values"]["client_secret"] == "***"


def test_configure_credential_missing_required_field_fails(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    with pytest.raises(CredentialError):
        configure_credential(state_dir, "company.slack-demo", "1.0.0", "ws_001", {"client_id": "demo-client"})


def test_test_credential_reports_presence(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    assert check_credential(state_dir, "company.slack-demo", "1.0.0", "ws_001")["ok"] is False

    configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )

    assert check_credential(state_dir, "company.slack-demo", "1.0.0", "ws_001")["ok"] is True


def test_invoke_requires_credential(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello"},
        user="user_001",
    )

    assert result.success is False
    assert result.error["code"] == "missing_credential"
    assert list_audit_records(state_dir)[0]["error_code"] == "missing_credential"


def test_sensitive_action_requires_confirmation(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello"},
        user="user_001",
    )

    assert result.success is False
    assert result.error["code"] == "sensitive_action_requires_confirmation"


def test_invoke_with_credential_and_confirmation_succeeds(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    configure_credential(
        state_dir,
        "company.slack-demo",
        "1.0.0",
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )

    result = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello"},
        user="user_001",
        confirm_sensitive=True,
    )

    assert result.success is True
    assert list_audit_records(state_dir)[-1]["success"] is True
    assert list_audit_records(state_dir)[-1]["input_keys"] == ["channel_id", "text"]


def test_cli_configure_credential_and_audit(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    env = {"PYTHONPATH": str(ROOT)}

    configure = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "configure-credential",
            "company.slack-demo",
            "--version",
            "1.0.0",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--values",
            '{"client_id":"demo-client","client_secret":"demo-secret"}',
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert configure.returncode == 0, configure.stderr
    assert "***" in configure.stdout

    invoke = subprocess.run(
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
            "--user",
            "user_001",
            "--confirm-sensitive",
            "--input",
            '{"channel_id":"C001","text":"hello"}',
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert invoke.returncode == 0, invoke.stderr

    audit = subprocess.run(
        [sys.executable, "-m", "plugin_poc.cli", "list-audit", "--state", str(state_dir)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert audit.returncode == 0, audit.stderr
    assert "user_001" in audit.stdout
