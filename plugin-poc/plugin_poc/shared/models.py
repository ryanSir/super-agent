from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

Manifest = dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    plugin_dir: Path
    manifest_path: Path
    manifest: Manifest
    referenced_files: tuple[Path, ...]


@dataclass(frozen=True)
class PackageResult:
    plugin_id: str
    version: str
    package_path: Path
    metadata_path: Path
    checksum: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PublishResult:
    plugin_id: str
    version: str
    registry_dir: Path
    package_path: Path
    metadata_path: Path
    index_path: Path
    checksum: str

