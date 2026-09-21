from fastapi import APIRouter, HTTPException, Request

from plugin_core_service.api.schemas import InstallationResponse, InstallRequest, PluginActionRequest
from plugin_management_service.manager.service import PluginManagerError, PluginManagerService

router = APIRouter()


@router.get("/installations/{plugin_id}", response_model=InstallationResponse)
def get_installation(request: Request, plugin_id: str) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(manager.get_installation(plugin_id).model_dump())
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations", response_model=InstallationResponse)
def install_plugin(request: Request, body: InstallRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.install(body.plugin_id, body.version).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations/enable", response_model=InstallationResponse)
def enable_plugin(request: Request, body: PluginActionRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.enable(body.plugin_id).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations/disable", response_model=InstallationResponse)
def disable_plugin(request: Request, body: PluginActionRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.disable(body.plugin_id).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
