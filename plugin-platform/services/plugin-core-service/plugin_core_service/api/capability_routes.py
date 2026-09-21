from fastapi import APIRouter, Request

from plugin_core_service.api.schemas import CapabilityDiscoveryResponse
from plugin_management_service.manager.capability_index import CapabilityIndexService

router = APIRouter()


@router.get("", response_model=CapabilityDiscoveryResponse)
def list_capabilities(request: Request) -> CapabilityDiscoveryResponse:
    index: CapabilityIndexService = request.app.state.capability_index_service
    return CapabilityDiscoveryResponse(
        capabilities=index.list_capabilities(),
    )
