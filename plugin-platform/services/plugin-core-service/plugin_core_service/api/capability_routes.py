from fastapi import APIRouter, Request

from plugin_core_service.api.schemas import CapabilityDiscoveryResponse
from plugin_management_service.manager.capability_index import CapabilityIndexService

router = APIRouter()


@router.get("/workspaces/{workspace_id}", response_model=CapabilityDiscoveryResponse)
def list_workspace_capabilities(request: Request, workspace_id: str) -> CapabilityDiscoveryResponse:
    index: CapabilityIndexService = request.app.state.capability_index_service
    return CapabilityDiscoveryResponse(
        workspace_id=workspace_id,
        capabilities=index.list_workspace_capabilities(workspace_id),
    )


@router.get("/workspaces/{workspace_id}/agents/{agent_id}", response_model=CapabilityDiscoveryResponse)
def list_agent_capabilities(
    request: Request,
    workspace_id: str,
    agent_id: str,
) -> CapabilityDiscoveryResponse:
    index: CapabilityIndexService = request.app.state.capability_index_service
    return CapabilityDiscoveryResponse(
        workspace_id=workspace_id,
        agent_id=agent_id,
        capabilities=index.list_agent_capabilities(workspace_id, agent_id),
    )
