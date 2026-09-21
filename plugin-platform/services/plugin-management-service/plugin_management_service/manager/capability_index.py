from plugin_contracts.capability import CapabilitySummary
from plugin_management_service.storage.repository import ManagerRepository, RegistryRepository


class CapabilityIndexService:
    def __init__(
        self,
        registry_repository: RegistryRepository,
        manager_repository: ManagerRepository,
    ) -> None:
        self.registry_repository = registry_repository
        self.manager_repository = manager_repository

    def list_capabilities(self) -> list[CapabilitySummary]:
        capabilities: list[CapabilitySummary] = []
        for installation in self.manager_repository.list_installations():
            if not installation.enabled:
                continue
            version = self.registry_repository.get_version(
                installation.plugin_id,
                installation.version,
            )
            if version:
                capabilities.extend(version.capabilities)
        return capabilities
