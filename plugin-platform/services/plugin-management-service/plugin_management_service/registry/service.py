from datetime import UTC, datetime
from pathlib import Path

from plugin_developer.packager import _file_sha256
from plugin_developer.validator import validate_plugin
from plugin_contracts.manifest import load_manifest
from plugin_management_service.storage.repository import PluginVersionRecord, RegistryRepository


class RegistryError(RuntimeError):
    pass


class RegistryService:
    def __init__(self, repository: RegistryRepository) -> None:
        self.repository = repository

    def publish_directory(self, plugin_dir: Path, package_path: Path) -> PluginVersionRecord:
        validation = validate_plugin(plugin_dir)
        if not validation.valid:
            messages = "; ".join(issue.message for issue in validation.issues)
            raise RegistryError(f"Plugin validation failed: {messages}")
        if not package_path.exists():
            raise RegistryError(f"Package not found: {package_path}")

        manifest = load_manifest(plugin_dir)
        record = PluginVersionRecord(
            plugin_id=manifest.plugin.id,
            version=manifest.plugin.version,
            checksum=_file_sha256(package_path),
            manifest=manifest,
            capabilities=validation.capabilities,
            package_path=str(package_path),
            created_at=datetime.now(UTC).isoformat(),
        )
        return self.repository.save_version(record)

    def get_version(self, plugin_id: str, version: str) -> PluginVersionRecord:
        record = self.repository.get_version(plugin_id, version)
        if not record:
            raise RegistryError(f"Plugin version not found: {plugin_id}@{version}")
        return record

    def list_versions(self) -> list[PluginVersionRecord]:
        return self.repository.list_versions()
