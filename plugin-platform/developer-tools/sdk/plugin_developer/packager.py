from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from plugin_developer.validator import validate_plugin
from plugin_contracts.manifest import load_manifest


@dataclass(frozen=True)
class PackageResult:
    plugin_id: str
    version: str
    checksum: str
    package_path: Path


class PackageError(RuntimeError):
    pass


def package_plugin(plugin_dir: Path, output_dir: Path) -> PackageResult:
    validation = validate_plugin(plugin_dir)
    if not validation.valid:
        messages = "; ".join(issue.message for issue in validation.issues)
        raise PackageError(f"Plugin validation failed: {messages}")

    manifest = load_manifest(plugin_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"{manifest.plugin.id}-{manifest.plugin.version}.zip"

    files = sorted(path for path in plugin_dir.rglob("*") if path.is_file())
    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(plugin_dir).as_posix())

    checksum = _file_sha256(package_path)
    return PackageResult(
        plugin_id=manifest.plugin.id,
        version=manifest.plugin.version,
        checksum=checksum,
        package_path=package_path,
    )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
