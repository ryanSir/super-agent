"""MCP 工具集成

通过 PydanticAI 原生 MCPServerStreamableHTTP 连接外部 MCP 服务，
将 MCP 工具自动注入 Orchestrator Agent。
"""

# 标准库
import json
from typing import Dict, List, Optional, Set

# 第三方库
from pydantic_ai.mcp import MCPServerStreamableHTTP

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 临时屏蔽的工具列表（格式不兼容或有问题的工具）
_BLOCKED_TOOLS: Set[str] = {"google_ai_search"}


def _apply_tool_filter(server: MCPServerStreamableHTTP) -> MCPServerStreamableHTTP:
    """在 server 实例上注入工具过滤逻辑，不修改类继承"""
    original_list_tools = server.list_tools

    async def filtered_list_tools():
        tools = await original_list_tools()
        filtered = [t for t in tools if t.name not in _BLOCKED_TOOLS]
        blocked = [t.name for t in tools if t.name in _BLOCKED_TOOLS]
        if blocked:
            logger.info(f"[MCP] 已过滤工具: {blocked}")
        return filtered

    server.list_tools = filtered_list_tools
    return server


def _parse_mcp_servers_config() -> List[Dict]:
    """解析 MCP_SERVERS 环境变量中的多端点配置

    Returns:
        端点配置列表，每项包含 name、url、headers（可选）
    """
    settings = get_settings()
    raw = settings.mcp.mcp_servers.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            logger.warning("[MCP] MCP_SERVERS 格式错误：应为 JSON 数组，回退到单端点")
            return []
        return data
    except json.JSONDecodeError as e:
        logger.warning(f"[MCP] MCP_SERVERS JSON 解析失败，回退到单端点 | error={e}")
        return []


def _create_server(url: str, headers: Optional[Dict[str, str]] = None) -> MCPServerStreamableHTTP:
    """创建一个新的 MCP Server 实例

    每次调用都创建新实例，避免跨请求复用导致 anyio cancel scope 状态污染。
    """
    server = MCPServerStreamableHTTP(
        url=url,
        headers=headers or {},
    )
    _apply_tool_filter(server)
    return server


def create_mcp_servers_from_config() -> List[MCPServerStreamableHTTP]:
    """从配置创建所有 MCP Server

    每次调用都返回全新的实例，因为 MCPServerStreamableHTTP 内部维护
    anyio cancel scope 等有状态资源，跨请求复用会导致 cancel scope 错误。

    优先读取 MCP_SERVERS（多端点 JSON 数组），回退到 MCP_SERVER_URL 单端点。

    Returns:
        MCP Server 实例列表
    """
    settings = get_settings()
    servers = []

    # 优先：多端点配置
    endpoint_configs = _parse_mcp_servers_config()
    if endpoint_configs:
        seen_names = set()
        for cfg in endpoint_configs:
            name = cfg.get("name", "")
            url = cfg.get("url", "")
            headers = cfg.get("headers", {})
            if not name or not url:
                logger.warning(f"[MCP] 跳过无效端点配置（缺少 name 或 url）| cfg={cfg}")
                continue
            if name in seen_names:
                logger.warning(f"[MCP] 端点名称重复，跳过 | name={name} url={url}")
                continue
            seen_names.add(name)
            try:
                server = _create_server(url=url, headers=headers)
                servers.append(server)
                logger.debug(f"[MCP] 创建 MCP Server | name={name} url={url}")
            except Exception as e:
                logger.error(f"[MCP] 端点创建失败，跳过 | name={name} url={url} error={e}")
        logger.info(f"[MCP] 多端点初始化完成 | servers={len(servers)}")
        return servers

    # 回退：单端点
    if settings.mcp.mcp_server_url:
        server = _create_server(url=settings.mcp.mcp_server_url)
        servers.append(server)
        logger.debug(f"[MCP] 创建 MCP Server | name=default url={settings.mcp.mcp_server_url}")

    logger.info(f"[MCP] 初始化完成 | servers={len(servers)}")
    return servers
