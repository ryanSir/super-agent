from pathlib import Path

import pytest

from plugin_core_service.config import PluginPlatformSettings


@pytest.fixture
def temp_settings(tmp_path: Path) -> PluginPlatformSettings:
    return PluginPlatformSettings(data_dir=tmp_path / "data")


@pytest.fixture
def example_plugin_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "plugins" / "research-assistant"
