from fastapi import APIRouter, HTTPException, Request

from plugin_core_service.api.schemas import (
    BindAgentRequest,
    InstallationResponse,
    InstallRequest,
    PluginActionRequest,
)
from plugin_management_service.manager.service import PluginManagerError, PluginManagerService

router = APIRouter()


@router.post("/installations", response_model=InstallationResponse)
def install_plugin(request: Request, body: InstallRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.install(body.workspace_id, body.plugin_id, body.version).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations/enable", response_model=InstallationResponse)
def enable_plugin(request: Request, body: PluginActionRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.enable(body.workspace_id, body.plugin_id).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations/disable", response_model=InstallationResponse)
def disable_plugin(request: Request, body: PluginActionRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.disable(body.workspace_id, body.plugin_id).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/installations/bind-agent", response_model=InstallationResponse)
def bind_agent(request: Request, body: BindAgentRequest) -> InstallationResponse:
    manager: PluginManagerService = request.app.state.manager_service
    try:
        return InstallationResponse.model_validate(
            manager.bind_agent(body.workspace_id, body.plugin_id, body.agent_id).model_dump()
        )
    except PluginManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
