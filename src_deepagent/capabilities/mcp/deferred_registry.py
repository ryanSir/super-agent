"""MCP 渐进式加载注册表

启动时只注册工具名称和描述，Agent 按需通过 tool_search 加载完整 schema。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeferredTool:
    """延迟加载的 MCP 工具元数据"""

    name: str
    description: str
    schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    loaded: bool = False


class DeferredToolRegistry:
    """MCP 工具延迟加载注册表

    启动时注册工具名称和描述（轻量），Agent 需要时通过 tool_search 加载完整 schema。
    """

    def __init__(self) -> None:
        self._tools: dict[str, DeferredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        schema: dict[str, Any] | None = None,
        server_name: str = "",
    ) -> None:
        """注册一个延迟加载工具"""
        self._tools[name] = DeferredTool(
            name=name,
            description=description,
            schema=schema or {},
            server_name=server_name,
        )

    def register_from_mcp(self, mcp_tools: list[dict[str, Any]]) -> int:
        """从 MCP 工具列表批量注册

        Args:
            mcp_tools: MCP 工具定义列表，每个包含 name/description/inputSchema

        Returns:
            注册数量
        """
        count = 0
        for tool in mcp_tools:
            name = tool.get("name", "")
            if not name:
                continue
            self.register(
                name=name,
                description=tool.get("description", ""),
                schema=tool.get("inputSchema", {}),
                server_name=tool.get("_server", ""),
            )
            count += 1
        logger.info(f"MCP 工具注册完成 | count={count}")
        return count

    def get_tool_names(self) -> list[str]:
        """获取所有工具名称（注入 system prompt）"""
        return sorted(self._tools.keys())

    def get_tool_summaries(self) -> list[dict[str, str]]:
        """获取工具名称+描述摘要"""
        return [
            {"name": t.name, "description": t.description}
            for t in sorted(self._tools.values(), key=lambda x: x.name)
        ]

    def search(self, query: str) -> list[DeferredTool]:
        """搜索工具

        支持三种模式：
        - "select:name1,name2" → 精确匹配
        - "+keyword rest" → 名称必须包含 keyword
        - "keyword query" → 正则匹配 name + description

        Args:
            query: 搜索查询

        Returns:
            匹配的工具列表
        """
        query = query.strip()

        # 模式1: 精确选择
        if query.startswith("select:"):
            names = [n.strip() for n in query[7:].split(",")]
            return [self._tools[n] for n in names if n in self._tools]

        # 模式2: 名称包含
        if query.startswith("+"):
            parts = query[1:].split()
            if not parts:
                return []
            keyword = parts[0].lower()
            return [
                t for t in self._tools.values()
                if keyword in t.name.lower()
            ]

        # 模式3: 正则匹配
        try:
            pattern = re.compile(query, re.IGNORECASE)
            return [
                t for t in self._tools.values()
                if pattern.search(t.name) or pattern.search(t.description)
            ]
        except re.error:
            # fallback: 简单子串匹配
            query_lower = query.lower()
            return [
                t for t in self._tools.values()
                if query_lower in t.name.lower() or query_lower in t.description.lower()
            ]

    def get(self, name: str) -> DeferredTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def __len__(self) -> int:
        return len(self._tools)


# 全局单例
deferred_tool_registry = DeferredToolRegistry()
