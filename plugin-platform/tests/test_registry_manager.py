from pathlib import Path

import pytest

from plugin_developer.packager import package_plugin
from plugin_management_service.manager.capability_index import CapabilityIndexService
from plugin_management_service.manager.service import PluginManagerError, PluginManagerService
from plugin_management_service.registry.service import RegistryService
from plugin_management_service.storage.local_store import DuplicatePluginVersionError, LocalPluginStore
from plugin_management_service.storage.repository import PluginVersionRecord


def test_registry_rejects_duplicate_version_with_different_checksum(
    tmp_path: Path,
    example_plugin_dir: Path,
) -> None:
    store = LocalPluginStore(tmp_path / "store")
    registry = RegistryService(store)
    package = package_plugin(example_plugin_dir, tmp_path / "packages")
    first = registry.publish_directory(example_plugin_dir, package.package_path)

    duplicate = PluginVersionRecord.model_validate(first.model_dump())
    duplicate.checksum = "0" * 64

    with pytest.raises(DuplicatePluginVersionError):
        store.save_version(duplicate)


def test_manager_rejects_missing_version(tmp_path: Path) -> None:
    store = LocalPluginStore(tmp_path / "store")
    manager = PluginManagerService(store, store)

    with pytest.raises(PluginManagerError):
        manager.install("workspace-1", "missing-plugin", "0.1.0")


def test_install_enable_disable_and_capability_index(
    tmp_path: Path,
    example_plugin_dir: Path,
) -> None:
    store = LocalPluginStore(tmp_path / "store")
    registry = RegistryService(store)
    manager = PluginManagerService(store, store)
    index = CapabilityIndexService(store, store)
    package = package_plugin(example_plugin_dir, tmp_path / "packages")
    registry.publish_directory(example_plugin_dir, package.package_path)

    installed = manager.install("workspace-1", "research-assistant", "0.1.0")
    assert not installed.enabled
    assert index.list_workspace_capabilities("workspace-1") == []

    enabled = manager.enable("workspace-1", "research-assistant")
    assert enabled.enabled
    assert len(index.list_workspace_capabilities("workspace-1")) == 3

    manager.bind_agent("workspace-1", "research-assistant", "agent-1")
    assert len(index.list_agent_capabilities("workspace-1", "agent-1")) == 3
    assert index.list_agent_capabilities("workspace-1", "agent-2") == []

    manager.disable("workspace-1", "research-assistant")
    assert index.list_workspace_capabilities("workspace-1") == []
