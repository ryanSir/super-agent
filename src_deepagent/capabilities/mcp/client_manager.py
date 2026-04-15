"""MCP 多端点管理器

负责解析 MCP_SERVERS 配置，创建 FastMCPToolset 实例，
作为 toolsets 传入 Agent，由框架自动管理连接生命周期和工具发现。
支持 SSE 和 Streamable HTTP 两种传输协议（无 headers 时自动推断）。
支持 default_args 自动注入固定参数（如 api_key），对 LLM 透明。
"""

from __future__ import annotations

import copy
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
    transport: str = ""  # "sse" | "streamable" | ""（空=自动推断）
    default_args: dict[str, Any] = field(default_factory=dict)  # 自动注入的固定参数


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
                        transport=item.get("transport", ""),
                        default_args=item.get("default_args", {}),
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


@dataclass
class DefaultArgsToolset:
    """包装 toolset，自动注入 default_args 并从 schema 中隐藏这些字段

    - get_tools: 从每个工具的 parameters_json_schema 中移除 default_args 对应的字段
    - call_tool: 调用前自动合并 default_args（LLM 传的值优先）
    """

    wrapped: Any  # AbstractToolset
    default_args: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str | None:
        return getattr(self.wrapped, "id", None)

    @property
    def label(self) -> str:
        return f"DefaultArgs({getattr(self.wrapped, 'label', '?')})"

    @property
    def tool_name_conflict_hint(self) -> str:
        return getattr(self.wrapped, "tool_name_conflict_hint", "")

    async def for_run(self, ctx: Any) -> Any:
        new_wrapped = await self.wrapped.for_run(ctx)
        if new_wrapped is self.wrapped:
            return self
        return DefaultArgsToolset(wrapped=new_wrapped, default_args=self.default_args)

    async def for_run_step(self, ctx: Any) -> Any:
        new_wrapped = await self.wrapped.for_run_step(ctx)
        if new_wrapped is self.wrapped:
            return self
        return DefaultArgsToolset(wrapped=new_wrapped, default_args=self.default_args)

    async def __aenter__(self) -> DefaultArgsToolset:
        await self.wrapped.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        return await self.wrapped.__aexit__(*args)

    async def get_instructions(self, ctx: Any) -> Any:
        return await self.wrapped.get_instructions(ctx)

    async def get_tools(self, ctx: Any) -> dict[str, Any]:
        from dataclasses import replace as dc_replace

        tools = await self.wrapped.get_tools(ctx)
        if not self.default_args:
            return tools

        patched: dict[str, Any] = {}
        for name, tool in tools.items():
            # 深拷贝 schema，移除 default_args 中的字段
            schema = copy.deepcopy(tool.tool_def.parameters_json_schema)
            props = schema.get("properties", {})
            required = schema.get("required", [])

            for arg_name in self.default_args:
                props.pop(arg_name, None)
                if arg_name in required:
                    required = [r for r in required if r != arg_name]

            schema["properties"] = props
            if required:
                schema["required"] = required
            else:
                schema.pop("required", None)

            new_def = dc_replace(tool.tool_def, parameters_json_schema=schema)
            patched[name] = dc_replace(tool, toolset=self, tool_def=new_def)

        return patched

    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx: Any, tool: Any) -> Any:
        # 合并 default_args（LLM 传的值优先）
        merged = {**self.default_args, **tool_args}
        return await self.wrapped.call_tool(name, merged, ctx, tool)

    def prefixed(self, prefix: str) -> Any:
        """支持链式调用 .prefixed()"""
        from pydantic_ai.toolsets.prefixed import PrefixedToolset
        return PrefixedToolset(wrapped=self, prefix=prefix)


def _create_mcp_toolset(ep: MCPEndpointConfig, use_prefix: bool) -> Any | None:
    """根据端点配置创建 FastMCPToolset 实例

    - 无 headers 且无显式 transport → 直接传 URL，自动推断协议
    - 有 headers 或显式指定 transport → 创建对应 transport 对象
    - 多端点时用 .prefixed(name) 做命名空间隔离
    - 有 default_args 时包装 DefaultArgsToolset，自动注入固定参数并从 schema 中隐藏

    Args:
        ep: 端点配置
        use_prefix: 多端点时用 name 作为 tool_prefix 避免冲突

    Returns:
        FastMCPToolset 实例，失败返回 None
    """
    from pydantic_ai.toolsets.fastmcp import FastMCPToolset

    # 需要显式指定 transport 的场景：有 headers 或指定了 transport 类型
    if ep.headers or ep.transport:
        from fastmcp.client.transports import SSETransport, StreamableHttpTransport

        if ep.transport == "sse":
            transport = SSETransport(url=ep.url, headers=ep.headers or None)
        elif ep.transport == "streamable":
            transport = StreamableHttpTransport(url=ep.url, headers=ep.headers or None)
        elif ep.transport:
            logger.warning(f"不支持的 transport 类型: '{ep.transport}'，跳过端点 '{ep.name}'")
            return None
        else:
            # 有 headers 但没指定 transport，默认 streamable
            transport = StreamableHttpTransport(url=ep.url, headers=ep.headers or None)

        toolset = FastMCPToolset(transport)
    else:
        # 无 headers 无显式 transport，传 URL 自动推断
        toolset = FastMCPToolset(ep.url)

    # 有 default_args 时包装一层，自动注入固定参数
    if ep.default_args:
        toolset = DefaultArgsToolset(wrapped=toolset, default_args=ep.default_args)

    if use_prefix:
        toolset = toolset.prefixed(ep.name)

    return toolset


class MCPClientManager:
    """MCP 多端点管理器

    将配置转换为 FastMCPToolset 实例，
    由 Agent 框架自动管理连接生命周期和工具发现。

    生命周期：setup() → get_toolsets() → refresh()（可选）
    """

    def __init__(self) -> None:
        self._servers: list[Any] = []  # FastMCPToolset instances
        self._endpoints: list[MCPEndpointConfig] = []

    def setup(self, endpoints: list[MCPEndpointConfig]) -> int:
        """根据端点配置创建 FastMCPToolset 实例

        Args:
            endpoints: 端点配置列表

        Returns:
            成功创建的 MCPServer 数量
        """
        use_prefix = len(endpoints) > 1
        servers: list[Any] = []

        for ep in endpoints:
            try:
                server = _create_mcp_toolset(ep, use_prefix=use_prefix)
                if server is not None:
                    servers.append(server)
                    logger.info(
                        f"MCP 端点已创建 | name={ep.name} "
                        f"transport={ep.transport} url={ep.url}"
                    )
            except Exception as e:
                logger.error(f"MCP 端点创建失败 | name={ep.name} error={e}")
                continue

        self._servers = servers
        self._endpoints = endpoints
        logger.info(f"MCP 管理器初始化完成 | servers={len(servers)}")
        return len(servers)

    def refresh(self) -> int:
        """重建所有 MCPServer 实例（原子替换）

        Returns:
            刷新后的 MCPServer 数量
        """
        if not self._endpoints:
            logger.info("[MCPClientManager] 无端点配置，跳过刷新")
            return 0
        return self.setup(self._endpoints)

    def get_toolsets(self) -> list[Any]:
        """返回 MCPServer toolset 列表，传入 create_deep_agent(toolsets=...)"""
        return list(self._servers)

    @property
    def connected_endpoints(self) -> list[str]:
        return [ep.name for ep in self._endpoints[:len(self._servers)]]

    @property
    def server_count(self) -> int:
        return len(self._servers)


# 全局单例
mcp_client_manager = MCPClientManager()
