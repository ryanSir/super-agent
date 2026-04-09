"""自定义 Agent 注册表

支持用户创建自定义 Agent 配置，系统加载后作为可用的 Sub-Agent。
类似 Skill 的注册机制，通过目录扫描发现 AGENT.md 配置文件。

目录结构：
  agents/
  ├── my-data-agent/
  │   └── AGENT.md          # YAML frontmatter 定义 Agent 配置
  └── my-code-reviewer/
      └── AGENT.md
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class CustomAgentConfig:
    """自定义 Agent 配置"""

    __slots__ = ("name", "description", "instructions", "model", "tools", "path")

    def __init__(
        self,
        name: str,
        description: str = "",
        instructions: str = "",
        model: str = "",
        tools: list[str] | None = None,
        path: str = "",
    ) -> None:
        self.name = name
        self.description = description
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self.path = path

    def to_sub_agent_config(self, tool_map: dict[str, Any]) -> dict[str, Any]:
        """转换为 SubAgentConfig 兼容的字典"""
        resolved_tools = [tool_map[t] for t in self.tools if t in tool_map]
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "model": self.model or None,
            "include_todo": True,
            "include_filesystem": False,
            "include_subagents": False,
            "include_skills": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": resolved_tools,
        }


class CustomAgentRegistry:
    """自定义 Agent 注册表

    扫描 agents/ 目录，解析 AGENT.md 配置，注册为可用的 Sub-Agent。
    """

    def __init__(self) -> None:
        self._agents: dict[str, CustomAgentConfig] = {}
        self._scanned = False

    def scan(self, agents_dir: str = "agents") -> int:
        """扫描 agents 目录

        Returns:
            发现的自定义 Agent 数量
        """
        agents_path = Path(agents_dir)
        if not agents_path.exists():
            logger.info(f"自定义 Agent 目录不存在，跳过 | path={agents_dir}")
            return 0

        count = 0
        for entry in agents_path.iterdir():
            if not entry.is_dir():
                continue
            agent_md = entry / "AGENT.md"
            if not agent_md.exists():
                continue

            config = self._parse_agent(entry, agent_md)
            if config:
                self._agents[config.name] = config
                count += 1

        self._scanned = True
        logger.info(f"自定义 Agent 扫描完成 | count={count} dir={agents_dir}")
        return count

    def list_agents(self) -> list[CustomAgentConfig]:
        """列出所有自定义 Agent"""
        return list(self._agents.values())

    def get(self, name: str) -> CustomAgentConfig | None:
        """按名称获取"""
        return self._agents.get(name)

    def get_role_descriptions(self) -> list[dict[str, str]]:
        """获取角色描述列表（注入 system prompt）"""
        return [
            {"name": a.name, "description": a.description}
            for a in self._agents.values()
        ]

    def to_sub_agent_configs(self, tool_map: dict[str, Any]) -> list[dict[str, Any]]:
        """转换为 SubAgentConfig 列表"""
        return [a.to_sub_agent_config(tool_map) for a in self._agents.values()]

    def _parse_agent(self, agent_dir: Path, agent_md: Path) -> CustomAgentConfig | None:
        """解析 AGENT.md"""
        try:
            content = agent_md.read_text(encoding="utf-8")
            name = agent_dir.name
            description = ""
            model = ""
            tools: list[str] = []

            match = _FRONTMATTER_RE.match(content)
            if match:
                for line in match.group(1).splitlines():
                    line = line.strip()
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("model:"):
                        model = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("tools:"):
                        tools_str = line.split(":", 1)[1].strip()
                        tools = [t.strip() for t in tools_str.strip("[]").split(",") if t.strip()]

            # frontmatter 之后的内容作为 instructions
            instructions = content
            if match:
                instructions = content[match.end():].strip()

            return CustomAgentConfig(
                name=name,
                description=description,
                instructions=instructions,
                model=model,
                tools=tools,
                path=str(agent_dir),
            )
        except Exception as e:
            logger.warning(f"自定义 Agent 解析失败 | dir={agent_dir} error={e}")
            return None


# 全局单例
custom_agent_registry = CustomAgentRegistry()
