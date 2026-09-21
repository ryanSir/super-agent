from pathlib import Path

from fastapi.testclient import TestClient

from plugin_core_service.api.app import create_app
from plugin_core_service.config import PluginPlatformSettings
from plugin_cli.packager import package_plugin


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
            "plugin_id": "research-assistant",
            "version": "0.1.0",
        },
    )
    assert install_response.status_code == 200
    assert install_response.json()["enabled"] is False

    get_install_response = client.get("/api/manager/installations/research-assistant")
    assert get_install_response.status_code == 200
    assert get_install_response.json()["plugin_id"] == "research-assistant"

    enable_response = client.post(
        "/api/manager/installations/enable",
        json={"plugin_id": "research-assistant"},
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True

    capabilities = client.get("/api/capabilities")
    assert capabilities.status_code == 200
    assert len(capabilities.json()["capabilities"]) == 3
