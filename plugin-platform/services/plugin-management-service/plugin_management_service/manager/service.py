from plugin_management_service.storage.repository import (
    InstallationRecord,
    ManagerRepository,
    RegistryRepository,
)


class PluginManagerError(RuntimeError):
    pass


class PluginManagerService:
    def __init__(
        self,
        registry_repository: RegistryRepository,
        manager_repository: ManagerRepository,
    ) -> None:
        self.registry_repository = registry_repository
        self.manager_repository = manager_repository

    def install(self, plugin_id: str, version: str) -> InstallationRecord:
        plugin_version = self.registry_repository.get_version(plugin_id, version)
        if not plugin_version:
            raise PluginManagerError(f"Plugin version not found: {plugin_id}@{version}")
        existing = self.manager_repository.get_installation(plugin_id)
        if existing:
            return existing
        return self.manager_repository.save_installation(
            InstallationRecord(
                plugin_id=plugin_id,
                version=version,
                enabled=False,
            )
        )

    def get_installation(self, plugin_id: str) -> InstallationRecord:
        return self._get_required_installation(plugin_id)

    def enable(self, plugin_id: str) -> InstallationRecord:
        record = self._get_required_installation(plugin_id)
        record.enabled = True
        return self.manager_repository.save_installation(record)

    def disable(self, plugin_id: str) -> InstallationRecord:
        record = self._get_required_installation(plugin_id)
        record.enabled = False
        return self.manager_repository.save_installation(record)

    def _get_required_installation(self, plugin_id: str) -> InstallationRecord:
        record = self.manager_repository.get_installation(plugin_id)
        if not record:
            raise PluginManagerError(f"Plugin is not installed: {plugin_id}")
        return record
