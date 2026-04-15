## 1. 数据模型与配置

- [x] 1.1 `config/settings.py` — `MCPEndpointConfig` 新增 `transport` 字段（`"sse"` | `"streamable"`，默认 `"streamable"`）
- [x] 1.2 `capabilities/mcp/client_manager.py` — `MCPEndpointConfig` dataclass 新增 `transport: str = "streamable"` 字段，`parse_mcp_servers` 解析 JSON 时读取 transport

## 2. 核心改造：MCPClientManager

- [x] 2.1 `capabilities/mcp/client_manager.py` — 新增 `_create_transport(ep)` 方法，根据 `ep.transport` 返回 `SSETransport` 或 `StreamableHttpTransport`，无效值记录 warning 并返回 None
- [x] 2.2 `capabilities/mcp/client_manager.py` — 改造 `connect()` 方法，使用 `_create_transport` 创建 transport 传入 `Client(transport=...)`，替代原来的 `Client(url)`
- [x] 2.3 `capabilities/mcp/client_manager.py` — 新增 `_wrap_mcp_tool(tool_name, description, schema, server_name)` 方法，将单个 MCP 工具包装为 `pydantic_ai.Tool` 对象
- [x] 2.4 `capabilities/mcp/client_manager.py` — 新增 `_tools: list[Tool]` 属性和 `get_tools() -> list[Tool]` 方法，connect 完成后构建 Tool 列表
- [x] 2.5 `capabilities/mcp/client_manager.py` — 改造 `refresh()` 方法，刷新时重新构建 `list[Tool]` 并原子替换 `_tools` 引用

## 3. 移除旧机制

- [x] 3.1 `capabilities/base_tools.py` — 移除 `tool_search` 和 `call_mcp_tool` 两个函数，以及 `create_base_tools` 返回列表中对应的引用
- [x] 3.2 删除 `capabilities/mcp/deferred_registry.py` 文件
- [x] 3.3 `capabilities/mcp/__init__.py` — 清理 deferred_registry 相关导入（如有）

## 4. 集成层改造

- [x] 4.1 `capabilities/registry.py` — `CapabilityRegistry` 移除 `_mcp_registry` 引用，改为从 `mcp_client_manager.get_tools()` 获取 MCP Tool 列表
- [x] 4.2 `context/builder.py` — 移除 `deferred_tool_names` 参数和 `<available_mcp_tools>` prompt 注入段落
- [x] 4.3 `orchestrator/reasoning_engine.py` — `_resolve_resources()` 移除 `deferred_tool_summaries` 获取逻辑，改为将 `mcp_client_manager.get_tools()` 合并到 agent tools 列表
- [x] 4.4 `orchestrator/reasoning_engine.py` — `_connect_mcp()` 移除 deferred_tool_registry 相关导入
- [x] 4.5 `context/templates/tool_usage.md` — 移除 `tool_search` / `call_mcp_tool` 的使用说明（如有）

## 5. 验证

- [x] 5.1 全局搜索 `deferred_tool_registry` / `tool_search` / `call_mcp_tool` 引用，确保无遗漏
- [x] 5.2 启动服务验证无 import 错误，MCP 未配置时正常降级
