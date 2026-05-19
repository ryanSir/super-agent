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

    def install(self, workspace_id: str, plugin_id: str, version: str) -> InstallationRecord:
        if not self.registry_repository.get_version(plugin_id, version):
            raise PluginManagerError(f"Plugin version not found: {plugin_id}@{version}")
        existing = self.manager_repository.get_installation(workspace_id, plugin_id)
        if existing:
            return existing
        return self.manager_repository.save_installation(
            InstallationRecord(
                workspace_id=workspace_id,
                plugin_id=plugin_id,
                version=version,
                enabled=False,
            )
        )

    def enable(self, workspace_id: str, plugin_id: str) -> InstallationRecord:
        record = self._get_required_installation(workspace_id, plugin_id)
        record.enabled = True
        return self.manager_repository.save_installation(record)

    def disable(self, workspace_id: str, plugin_id: str) -> InstallationRecord:
        record = self._get_required_installation(workspace_id, plugin_id)
        record.enabled = False
        return self.manager_repository.save_installation(record)

    def bind_agent(self, workspace_id: str, plugin_id: str, agent_id: str) -> InstallationRecord:
        record = self._get_required_installation(workspace_id, plugin_id)
        if agent_id not in record.agent_ids:
            record.agent_ids.append(agent_id)
        return self.manager_repository.save_installation(record)

    def _get_required_installation(self, workspace_id: str, plugin_id: str) -> InstallationRecord:
        record = self.manager_repository.get_installation(workspace_id, plugin_id)
        if not record:
            raise PluginManagerError(f"Plugin is not installed: {workspace_id}/{plugin_id}")
        return record
