from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException, Request, UploadFile

from plugin_core_service.api.schemas import PublishResponse
from plugin_management_service.registry.service import RegistryError, RegistryService
from plugin_management_service.storage.local_store import DuplicatePluginVersionError

router = APIRouter()


@router.post("/packages", response_model=PublishResponse)
async def publish_package(request: Request, package: UploadFile) -> PublishResponse:
    settings = request.app.state.settings
    registry: RegistryService = request.app.state.registry_service
    package_dir = Path(settings.resolved_package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    saved_package = package_dir / package.filename
    saved_package.write_bytes(await package.read())

    with TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugin"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(saved_package) as archive:
            archive.extractall(plugin_dir)
        try:
            record = registry.publish_directory(plugin_dir, saved_package)
        except (RegistryError, DuplicatePluginVersionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PublishResponse(
        plugin_id=record.plugin_id,
        version=record.version,
        checksum=record.checksum,
        status=record.status,
    )


@router.get("/plugins")
def list_plugins(request: Request) -> list[dict[str, object]]:
    registry: RegistryService = request.app.state.registry_service
    return [record.model_dump(mode="json") for record in registry.list_versions()]


@router.get("/plugins/{plugin_id}/versions/{version}")
def get_plugin_version(request: Request, plugin_id: str, version: str) -> dict[str, object]:
    registry: RegistryService = request.app.state.registry_service
    try:
        return registry.get_version(plugin_id, version).model_dump(mode="json")
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
