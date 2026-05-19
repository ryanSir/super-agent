from pathlib import Path

import pytest

from plugin_developer.packager import PackageError, package_plugin
from plugin_developer.validator import validate_plugin


def test_validate_example_plugin_success(example_plugin_dir: Path) -> None:
    result = validate_plugin(example_plugin_dir)

    assert result.valid
    assert result.plugin_id == "research-assistant"
    assert {cap.name for cap in result.capabilities} == {
        "research-summary",
        "patent-search",
        "literature-mcp",
    }


def test_validate_missing_reference(tmp_path: Path, example_plugin_dir: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    _copy_tree(example_plugin_dir, plugin_dir)
    (plugin_dir / "skills" / "research-summary.md").unlink()

    result = validate_plugin(plugin_dir)

    assert not result.valid
    assert any(issue.code == "referenced_file_missing" for issue in result.issues)


def test_validate_rejects_stdio_mcp(tmp_path: Path, example_plugin_dir: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    _copy_tree(example_plugin_dir, plugin_dir)
    manifest = plugin_dir / "plugin.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("streamable-http", "stdio"),
        encoding="utf-8",
    )

    result = validate_plugin(plugin_dir)

    assert not result.valid
    assert any(issue.code == "unsupported_mcp_transport" for issue in result.issues)


def test_package_plugin_success(tmp_path: Path, example_plugin_dir: Path) -> None:
    result = package_plugin(example_plugin_dir, tmp_path)

    assert result.plugin_id == "research-assistant"
    assert result.version == "0.1.0"
    assert result.package_path.exists()
    assert len(result.checksum) == 64


def test_package_stops_when_validation_fails(tmp_path: Path, example_plugin_dir: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    _copy_tree(example_plugin_dir, plugin_dir)
    (plugin_dir / "openapi" / "patent-search.yaml").unlink()

    with pytest.raises(PackageError):
        package_plugin(plugin_dir, tmp_path / "packages")


def _copy_tree(source: Path, target: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())
