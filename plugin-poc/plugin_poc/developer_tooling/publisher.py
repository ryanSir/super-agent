from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ..shared.errors import PublishError
from ..shared.io import dump_json, dump_yaml
from ..shared.models import PublishResult
from .packager import build_package


def publish_plugin(plugin_dir: str | Path, registry_dir: str | Path, force: bool = False) -> PublishResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        package = build_package(plugin_dir, temp_dir)
        return _publish_package(package, registry_dir, force)


def _publish_package(package, registry_dir: str | Path, force: bool) -> PublishResult:
    registry = Path(registry_dir).resolve()
    package_dir = registry / "packages" / package.plugin_id / package.version

    if package_dir.exists() and not force:
        raise PublishError(f"plugin version already exists: {package.plugin_id}@{package.version}")

    package_dir.mkdir(parents=True, exist_ok=True)
    target_package = package_dir / "package.zip"
    target_metadata = package_dir / "metadata.json"
    target_manifest = package_dir / "manifest.yaml"

    shutil.copy2(package.package_path, target_package)
    shutil.copy2(package.metadata_path, target_metadata)
    dump_yaml(target_manifest, package.metadata["manifest"])

    index_path = registry / "index.json"
    index = _load_index(index_path)
    entry = {
        "plugin_id": package.plugin_id,
        "version": package.version,
        "name": package.metadata["name"],
        "description": package.metadata.get("description", ""),
        "author": package.metadata.get("author", ""),
        "checksum": package.checksum,
        "package_path": target_package.relative_to(registry).as_posix(),
        "metadata_path": target_metadata.relative_to(registry).as_posix(),
        "published_at": datetime.now(UTC).isoformat(),
    }

    plugins = index.setdefault("plugins", {})
    versions = plugins.setdefault(package.plugin_id, {})
    versions[package.version] = entry
    dump_json(index_path, index)

    return PublishResult(
        plugin_id=package.plugin_id,
        version=package.version,
        registry_dir=registry,
        package_path=target_package,
        metadata_path=target_metadata,
        index_path=index_path,
        checksum=package.checksum,
    )


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"schema_version": "0.1.0", "plugins": {}}
    try:
        with index_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise PublishError(f"invalid registry index: {index_path}") from exc
    if not isinstance(data, dict):
        raise PublishError(f"registry index must be an object: {index_path}")
    data.setdefault("schema_version", "0.1.0")
    data.setdefault("plugins", {})
    return data
