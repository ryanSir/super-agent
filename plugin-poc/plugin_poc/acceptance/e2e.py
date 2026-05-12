from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.credentials import configure_credential
from ..core.gateway import invoke_capability
from ..developer_tooling.publisher import publish_plugin
from ..management.manager import enable_plugin, install_plugin, list_capabilities
from ..runtime_host import runtime_health, start_runtime
from ..runtimes.skill_runtime import render_skill_context


def run_local_e2e(plugin_dir: str | Path, registry_dir: str | Path, state_dir: str | Path) -> dict[str, Any]:
    publish = publish_plugin(plugin_dir, registry_dir, force=True)
    install = install_plugin(registry_dir, state_dir, publish.plugin_id, publish.version)
    enable = enable_plugin(state_dir, publish.plugin_id, publish.version, "ws_001", "agent_001")
    credential = configure_credential(
        state_dir,
        publish.plugin_id,
        publish.version,
        "ws_001",
        {"client_id": "demo-client", "client_secret": "demo-secret"},
    )
    runtime = start_runtime(state_dir, publish.plugin_id, publish.version)
    tool = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.tool.send_message",
        {"channel_id": "C001", "text": "hello from e2e"},
        user="user_001",
        confirm_sensitive=True,
    )
    data_source = invoke_capability(
        state_dir,
        "ws_001",
        "agent_001",
        "company.slack-demo.datasource.slack_messages",
        {"query": "plugin", "limit": 2},
        user="user_001",
    )
    skill_context = render_skill_context(state_dir, "ws_001", "agent_001")
    health = runtime_health(state_dir, publish.plugin_id, publish.version)

    return {
        "status": "ok" if tool.success and data_source.success else "error",
        "publish": {"plugin_id": publish.plugin_id, "version": publish.version},
        "install": install,
        "enable": enable,
        "credential": credential,
        "runtime": runtime,
        "health": health,
        "capability_count": len(list_capabilities(state_dir, "ws_001", "agent_001")),
        "tool_invocation": tool.to_dict(),
        "data_source_invocation": data_source.to_dict(),
        "skill_context": skill_context,
    }
