from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from plugin_poc.developer_tooling.publisher import publish_plugin
from plugin_poc.management.manager import enable_plugin, install_plugin
from plugin_poc.runtimes.skill_runtime import list_agent_skills, parse_skill_file, render_skill_context

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "slack-demo"


def prepare_enabled_plugin(tmp_path: Path) -> Path:
    plugin_dir = tmp_path / "slack-demo"
    shutil.copytree(EXAMPLE, plugin_dir)
    registry_dir = tmp_path / "registry"
    state_dir = tmp_path / "state"
    publish_plugin(plugin_dir, registry_dir)
    install_plugin(registry_dir, state_dir, "company.slack-demo", "1.0.0")
    enable_plugin(state_dir, "company.slack-demo", "1.0.0", "ws_001", "agent_001")
    return state_dir


def test_parse_skill_file_reads_frontmatter() -> None:
    metadata, content = parse_skill_file(EXAMPLE / "skills" / "summarize-channel" / "SKILL.md")

    assert metadata["name"] == "summarize-channel"
    assert metadata["description"] == "Summarize recent channel messages."
    assert "Use the Slack message data source" in content


def test_list_agent_skills_returns_enabled_skill_metadata(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    skills = list_agent_skills(state_dir, "ws_001", "agent_001")

    assert skills == [
        {
            "capability_id": "company.slack-demo.skill.summarize-channel",
            "plugin_id": "company.slack-demo",
            "version": "1.0.0",
            "name": "summarize-channel",
            "description": "Summarize recent channel messages.",
            "source": "skills/summarize-channel/SKILL.md",
            "metadata": {
                "name": "summarize-channel",
                "description": "Summarize recent channel messages.",
            },
        }
    ]


def test_render_skill_context_for_agent(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)

    context = render_skill_context(state_dir, "ws_001", "agent_001")

    assert "# Available Plugin Skills" in context
    assert "## summarize-channel" in context
    assert "Plugin: company.slack-demo@1.0.0" in context
    assert "Use the Slack message data source" in context


def test_cli_list_skills_and_render_context(tmp_path: Path) -> None:
    state_dir = prepare_enabled_plugin(tmp_path)
    env = {"PYTHONPATH": str(ROOT)}

    list_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "list-skills",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert list_result.returncode == 0, list_result.stderr
    assert "company.slack-demo.skill.summarize-channel" in list_result.stdout

    context_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "plugin_poc.cli",
            "render-skill-context",
            "--state",
            str(state_dir),
            "--workspace",
            "ws_001",
            "--agent",
            "agent_001",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert context_result.returncode == 0, context_result.stderr
    assert "Available Plugin Skills" in context_result.stdout
