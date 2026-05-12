from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from plugin_poc.developer_tooling.packager import build_package
from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.developer_tooling.validator import validate_plugin
from plugin_poc.shared.errors import PublishError, ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "slack-demo"


def copy_example(tmp_path: Path) -> Path:
    target = tmp_path / "slack-demo"
    shutil.copytree(EXAMPLE, target)
    return target


def test_validate_plugin_success(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)

    result = validate_plugin(plugin_dir)

    assert result.manifest["id"] == "company.slack-demo"
    assert result.manifest["version"] == "1.0.0"
    assert len(result.referenced_files) == 5


def test_validate_plugin_missing_required_field(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    manifest_path = plugin_dir / "plugin.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest.pop("id")
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    with pytest.raises(ValidationError) as exc_info:
        validate_plugin(plugin_dir)

    assert "missing required field: id" in exc_info.value.errors


def test_validate_plugin_missing_child_file(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    (plugin_dir / "tools" / "slack-tools.yaml").unlink()

    with pytest.raises(ValidationError) as exc_info:
        validate_plugin(plugin_dir)

    assert any("points to missing file" in error for error in exc_info.value.errors)


def test_build_package_creates_zip_metadata_and_checksums(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    output_dir = tmp_path / "dist"

    result = build_package(plugin_dir, output_dir)

    assert result.package_path.exists()
    assert result.metadata_path.exists()
    with ZipFile(result.package_path) as archive:
        names = set(archive.namelist())
    assert "plugin.yaml" in names
    assert "package.json" in names
    assert "checksums.json" in names
    assert "tools/slack-tools.yaml" in names


def test_publish_plugin_writes_registry_index(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    registry_dir = tmp_path / "registry"

    result = publish_plugin(plugin_dir, registry_dir)

    assert result.package_path.exists()
    index = json.loads((registry_dir / "index.json").read_text())
    entry = index["plugins"]["company.slack-demo"]["1.0.0"]
    assert entry["checksum"] == result.checksum


def test_publish_duplicate_without_force_fails(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    registry_dir = tmp_path / "registry"
    publish_plugin(plugin_dir, registry_dir)

    with pytest.raises(PublishError):
        publish_plugin(plugin_dir, registry_dir)


def test_cli_validate_package_publish(tmp_path: Path) -> None:
    plugin_dir = copy_example(tmp_path)
    registry_dir = tmp_path / "registry"
    env_path = str(ROOT)

    validate = subprocess.run(
        [sys.executable, "-m", "plugin_poc.cli", "validate", str(plugin_dir)],
        cwd=ROOT,
        env={"PYTHONPATH": env_path},
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr

    package = subprocess.run(
        [sys.executable, "-m", "plugin_poc.cli", "package", str(plugin_dir), "--output", str(tmp_path / "dist")],
        cwd=ROOT,
        env={"PYTHONPATH": env_path},
        text=True,
        capture_output=True,
        check=False,
    )
    assert package.returncode == 0, package.stderr

    publish = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "publish",
            str(plugin_dir),
            "--registry",
            str(registry_dir),
        ],
        cwd=ROOT,
        env={"PYTHONPATH": env_path},
        text=True,
        capture_output=True,
        check=False,
    )
    assert publish.returncode == 0, publish.stderr
    assert (registry_dir / "index.json").exists()
