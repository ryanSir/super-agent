from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ..shared.errors import PackageError
from ..shared.io import dump_json, dump_yaml, sha256_file
from ..shared.models import PackageResult
from .validator import validate_plugin

EXCLUDED_NAMES = {"__pycache__", ".DS_Store", ".plugin-registry"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def build_package(plugin_dir: str | Path, output_dir: str | Path | None = None) -> PackageResult:
    validation = validate_plugin(plugin_dir)
    manifest = validation.manifest
    plugin_id = manifest["id"]
    version = manifest["version"]
    root = validation.plugin_dir
    output = Path(output_dir).resolve() if output_dir else root / "dist"
    output.mkdir(parents=True, exist_ok=True)

    package_name = f"{plugin_id}-{version}.zip"
    package_path = output / package_name
    metadata_path = output / f"{plugin_id}-{version}.metadata.json"

    package_metadata = {
        "plugin_id": plugin_id,
        "version": version,
        "name": manifest["name"],
        "description": manifest.get("description", ""),
        "author": manifest.get("author", ""),
        "schema_version": manifest.get("schema_version"),
        "manifest": manifest,
    }
    metadata = dict(package_metadata)
    metadata["created_at"] = datetime.now(UTC).isoformat()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        package_metadata_path = temp_root / "package.json"
        checksums_path = temp_root / "checksums.json"
        dump_json(package_metadata_path, package_metadata)

        files = _collect_files(root, output)
        checksums = _build_checksums(root, files, package_metadata_path)
        dump_json(checksums_path, checksums)

        try:
            with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
                for file_path in files:
                    _write_stable_file(archive, file_path.relative_to(root).as_posix(), file_path.read_bytes())
                _write_stable_file(archive, "package.json", package_metadata_path.read_bytes())
                _write_stable_file(archive, "checksums.json", checksums_path.read_bytes())
        except Exception as exc:  # noqa: BLE001 - convert to domain error for CLI users
            raise PackageError(f"failed to build package: {exc}") from exc

    package_checksum = sha256_file(package_path)
    metadata["package"] = {
        "filename": package_name,
        "sha256": package_checksum,
    }
    dump_json(metadata_path, metadata)
    return PackageResult(
        plugin_id=plugin_id,
        version=version,
        package_path=package_path,
        metadata_path=metadata_path,
        checksum=package_checksum,
        metadata=metadata,
    )


def write_manifest_snapshot(path: Path, manifest: dict) -> None:
    dump_yaml(path, manifest)


def _collect_files(root: Path, output: Path) -> list[Path]:
    output = output.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if _is_excluded(path, root, output):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _is_excluded(path: Path, root: Path, output: Path) -> bool:
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    rel_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_NAMES for part in rel_parts):
        return True
    try:
        path.resolve().relative_to(output)
        return True
    except ValueError:
        return False


def _build_checksums(root: Path, files: list[Path], package_metadata_path: Path) -> dict[str, str]:
    checksums = {file_path.relative_to(root).as_posix(): sha256_file(file_path) for file_path in files}
    checksums["package.json"] = sha256_file(package_metadata_path)
    return dict(sorted(checksums.items()))


def _write_stable_file(archive: ZipFile, name: str, content: bytes) -> None:
    info = ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, content)
