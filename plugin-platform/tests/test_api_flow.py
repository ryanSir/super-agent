from pathlib import Path

from fastapi.testclient import TestClient

from plugin_core_service.api.app import create_app
from plugin_core_service.config import PluginPlatformSettings
from plugin_developer.packager import package_plugin


def test_publish_install_enable_and_discover_api_flow(
    tmp_path: Path,
    example_plugin_dir: Path,
) -> None:
    settings = PluginPlatformSettings(data_dir=tmp_path / "data")
    client = TestClient(create_app(settings))
    package = package_plugin(example_plugin_dir, tmp_path / "packages")

    with package.package_path.open("rb") as package_file:
        publish_response = client.post(
            "/api/registry/packages",
            files={"package": (package.package_path.name, package_file, "application/zip")},
        )

    assert publish_response.status_code == 200
    assert publish_response.json()["plugin_id"] == "research-assistant"

    install_response = client.post(
        "/api/manager/installations",
        json={
            "workspace_id": "workspace-1",
            "plugin_id": "research-assistant",
            "version": "0.1.0",
        },
    )
    assert install_response.status_code == 200
    assert install_response.json()["enabled"] is False

    enable_response = client.post(
        "/api/manager/installations/enable",
        json={"workspace_id": "workspace-1", "plugin_id": "research-assistant"},
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True

    bind_response = client.post(
        "/api/manager/installations/bind-agent",
        json={
            "workspace_id": "workspace-1",
            "plugin_id": "research-assistant",
            "agent_id": "agent-1",
        },
    )
    assert bind_response.status_code == 200

    workspace_capabilities = client.get("/api/capabilities/workspaces/workspace-1")
    assert workspace_capabilities.status_code == 200
    assert len(workspace_capabilities.json()["capabilities"]) == 3

    agent_capabilities = client.get("/api/capabilities/workspaces/workspace-1/agents/agent-1")
    assert agent_capabilities.status_code == 200
    assert len(agent_capabilities.json()["capabilities"]) == 3
