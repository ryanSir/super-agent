from pathlib import Path

from plugin_management_service.storage.repository import (
    InstallationRecord,
    PluginVersionRecord,
)


class DuplicatePluginVersionError(RuntimeError):
    pass


class LocalPluginStore:
    """Local development store with JSON files and replaceable repository methods."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.registry_dir = root_dir / "registry"
        self.install_dir = root_dir / "installations"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.install_dir.mkdir(parents=True, exist_ok=True)

    def save_version(self, record: PluginVersionRecord) -> PluginVersionRecord:
        path = self._version_path(record.plugin_id, record.version)
        existing = self.get_version(record.plugin_id, record.version)
        if existing and existing.checksum != record.checksum:
            raise DuplicatePluginVersionError(
                f"Plugin version already exists with different checksum: "
                f"{record.plugin_id}@{record.version}"
            )
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get_version(self, plugin_id: str, version: str) -> PluginVersionRecord | None:
        path = self._version_path(plugin_id, version)
        if not path.exists():
            return None
        return PluginVersionRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list_versions(self) -> list[PluginVersionRecord]:
        records = []
        for path in sorted(self.registry_dir.glob("*/*.json")):
            records.append(PluginVersionRecord.model_validate_json(path.read_text(encoding="utf-8")))
        return records

    def save_installation(self, record: InstallationRecord) -> InstallationRecord:
        path = self._installation_path(record.workspace_id, record.plugin_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get_installation(
        self,
        workspace_id: str,
        plugin_id: str,
    ) -> InstallationRecord | None:
        path = self._installation_path(workspace_id, plugin_id)
        if not path.exists():
            return None
        return InstallationRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list_installations(self, workspace_id: str) -> list[InstallationRecord]:
        workspace_dir = self.install_dir / workspace_id
        if not workspace_dir.exists():
            return []
        return [
            InstallationRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(workspace_dir.glob("*.json"))
        ]

    def _version_path(self, plugin_id: str, version: str) -> Path:
        plugin_dir = self.registry_dir / plugin_id
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir / f"{version}.json"

    def _installation_path(self, workspace_id: str, plugin_id: str) -> Path:
        return self.install_dir / workspace_id / f"{plugin_id}.json"
