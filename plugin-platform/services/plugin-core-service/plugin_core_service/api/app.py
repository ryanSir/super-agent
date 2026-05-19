from pathlib import Path

from fastapi import FastAPI

from plugin_core_service.api.capability_routes import router as capability_router
from plugin_core_service.api.manager_routes import router as manager_router
from plugin_core_service.api.registry_routes import router as registry_router
from plugin_core_service.config import PluginPlatformSettings, get_settings
from plugin_management_service.manager.capability_index import CapabilityIndexService
from plugin_management_service.manager.service import PluginManagerService
from plugin_management_service.registry.service import RegistryService
from plugin_management_service.storage.local_store import LocalPluginStore


def create_app(settings: PluginPlatformSettings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    store = LocalPluginStore(Path(resolved_settings.data_dir))

    app = FastAPI(title="Plugin Platform", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.store = store
    app.state.registry_service = RegistryService(store)
    app.state.manager_service = PluginManagerService(store, store)
    app.state.capability_index_service = CapabilityIndexService(store, store)

    app.include_router(registry_router, prefix="/api/registry", tags=["registry"])
    app.include_router(manager_router, prefix="/api/manager", tags=["manager"])
    app.include_router(capability_router, prefix="/api/capabilities", tags=["capabilities"])
    return app


app = create_app()
