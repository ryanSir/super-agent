"""MCP 多端点客户端管理器

负责解析 MCP_SERVERS 配置、建立连接、发现工具并注册到 deferred_tool_registry，
以及提供 call_tool 执行入口。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPEndpointConfig:
    """单个 MCP 端点配置"""

    name: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)


def parse_mcp_servers(servers_json: str, fallback_url: str) -> list[MCPEndpointConfig]:
    """解析 MCP 端点配置

    优先使用 MCP_SERVERS JSON 数组，fallback 到 MCP_SERVER_URL 单端点。
    """
    if servers_json and servers_json.strip():
        try:
            raw = json.loads(servers_json)
            if not isinstance(raw, list):
                logger.warning("MCP_SERVERS 不是 JSON 数组，回退到单端点")
            else:
                seen: dict[str, MCPEndpointConfig] = {}
                for item in raw:
                    name = item.get("name", "")
                    url = item.get("url", "")
                    if not name or not url:
                        logger.warning(f"MCP 端点配置缺少 name 或 url，跳过: {item}")
                        continue
                    if name in seen:
                        logger.warning(f"MCP 端点名称重复: '{name}'，使用最后一个配置")
                    seen[name] = MCPEndpointConfig(
                        name=name,
                        url=url,
                        headers=item.get("headers", {}),
                    )
                if seen:
                    endpoints = list(seen.values())
                    logger.info(
                        f"MCP 多端点配置解析完成 | count={len(endpoints)} "
                        f"names={[e.name for e in endpoints]}"
                    )
                    return endpoints
        except json.JSONDecodeError as e:
            logger.warning(f"MCP_SERVERS JSON 解析失败: {e}，回退到单端点")

    # fallback: MCP_SERVER_URL
    if fallback_url and fallback_url.strip():
        logger.info(f"使用单端点 MCP_SERVER_URL: {fallback_url}")
        return [MCPEndpointConfig(name="default", url=fallback_url.strip())]

    logger.info("未配置 MCP 端点")
    return []


class MCPClientManager:
    """MCP 多端点客户端管理器

    生命周期：connect() → (list_tools / call_tool) → close()
    """

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}  # name → fastmcp Client
        self._tool_to_server: dict[str, str] = {}  # tool_name → server_name
        self._endpoints: list[MCPEndpointConfig] = []  # 保存端点配置供 refresh 使用

    async def connect(self, endpoints: list[MCPEndpointConfig]) -> int:
        """连接所有 MCP 端点并发现工具

        Returns:
            成功注册的工具总数
        """
        from fastmcp.client import Client

        from src_deepagent.capabilities.mcp.deferred_registry import deferred_tool_registry

        total_tools = 0

        for ep in endpoints:
            try:
                logger.info(f"连接 MCP 端点 | name={ep.name} url={ep.url}")
                client = Client(ep.url)
                await client.__aenter__()
                self._clients[ep.name] = client

                tools = await client.list_tools()
                for tool in tools:
                    tool_name = tool.name
                    if tool_name in self._tool_to_server:
                        existing_server = self._tool_to_server[tool_name]
                        if existing_server != ep.name:
                            tool_name = f"{ep.name}:{tool.name}"
                            logger.warning(
                                f"工具名冲突: '{tool.name}' 已存在于 '{existing_server}'，"
                                f"重命名为 '{tool_name}'"
                            )

                    self._tool_to_server[tool_name] = ep.name
                    deferred_tool_registry.register(
                        name=tool_name,
                        description=tool.description or "",
                        schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        server_name=ep.name,
                    )
                    total_tools += 1

                logger.info(f"MCP 端点连接成功 | name={ep.name} tools={len(tools)}")

            except Exception as e:
                logger.error(f"MCP 端点连接失败 | name={ep.name} url={ep.url} error={e}")
                continue

        self._endpoints = endpoints
        logger.info(f"MCP 客户端管理器初始化完成 | endpoints={len(self._clients)} tools={total_tools}")
        return total_tools

    async def refresh(self) -> int:
        """重新发现所有端点的工具列表，原子替换，避免清空后的空窗口

        先在临时结构里构建新状态，全部成功后一次性替换，失败则保留旧状态。
        Returns:
            刷新后的工具总数
        """
        from src_deepagent.capabilities.mcp.deferred_registry import deferred_tool_registry, DeferredTool

        if not self._clients:
            logger.info("[MCPClientManager] 无已连接端点，跳过刷新")
            return 0

        new_tool_to_server: dict[str, str] = {}
        new_tools: list[DeferredTool] = []
        failed_endpoints: list[str] = []

        for ep_name, client in self._clients.items():
            try:
                tools = await client.list_tools()
                for tool in tools:
                    tool_name = tool.name
                    if tool_name in new_tool_to_server:
                        existing_server = new_tool_to_server[tool_name]
                        if existing_server != ep_name:
                            tool_name = f"{ep_name}:{tool.name}"
                    new_tool_to_server[tool_name] = ep_name
                    new_tools.append(DeferredTool(
                        name=tool_name,
                        description=tool.description or "",
                        schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        server_name=ep_name,
                    ))
                logger.info(f"[MCPClientManager] 刷新采集完成 | endpoint={ep_name} tools={len(tools)}")
            except Exception as e:
                logger.error(f"[MCPClientManager] 刷新失败 | endpoint={ep_name} error={e}")
                failed_endpoints.append(ep_name)

        if failed_endpoints and not new_tools:
            # 全部失败，保留旧状态
            logger.error(f"[MCPClientManager] 所有端点刷新失败，保留旧状态 | failed={failed_endpoints}")
            return len(self._tool_to_server)

        # 原子替换
        self._tool_to_server = new_tool_to_server
        deferred_tool_registry.replace(new_tools)

        logger.info(f"[MCPClientManager] 全量刷新完成 | total_tools={len(new_tools)} failed={failed_endpoints}")
        return len(new_tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """执行 MCP 工具

        Args:
            tool_name: 工具名称（可能带 server: 前缀）
            arguments: 工具参数

        Returns:
            执行结果
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return {"success": False, "error": f"未知的 MCP 工具: '{tool_name}'"}

        client = self._clients.get(server_name)
        if not client:
            return {"success": False, "error": f"MCP 端点 '{server_name}' 未连接"}

        # 如果 tool_name 带了 server: 前缀，还原为原始名称
        actual_name = tool_name
        prefix = f"{server_name}:"
        if tool_name.startswith(prefix):
            actual_name = tool_name[len(prefix):]

        try:
            logger.info(f"调用 MCP 工具 | tool={actual_name} server={server_name}")
            result = await client.call_tool(actual_name, arguments or {})

            # 解析 CallToolResult
            content_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    content_parts.append(item.text)
                elif hasattr(item, "data"):
                    content_parts.append(str(item.data))
                else:
                    content_parts.append(str(item))

            output = "\n".join(content_parts)

            return {
                "success": not getattr(result, "is_error", getattr(result, "isError", False)),
                "data": output,
                "server": server_name,
                "tool": actual_name,
            }

        except Exception as e:
            logger.error(f"MCP 工具执行失败 | tool={actual_name} server={server_name} error={e}")
            return {"success": False, "error": str(e), "server": server_name, "tool": actual_name}

    async def close(self) -> None:
        """关闭所有 MCP 连接"""
        for name, client in self._clients.items():
            try:
                await client.__aexit__(None, None, None)
                logger.info(f"MCP 端点已关闭 | name={name}")
            except Exception as e:
                logger.warning(f"MCP 端点关闭失败 | name={name} error={e}")
        self._clients.clear()
        self._tool_to_server.clear()

    @property
    def connected_endpoints(self) -> list[str]:
        return list(self._clients.keys())

    @property
    def tool_count(self) -> int:
        return len(self._tool_to_server)


# 全局单例
mcp_client_manager = MCPClientManager()
