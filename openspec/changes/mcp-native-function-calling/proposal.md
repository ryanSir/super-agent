## Why

当前 MCP 工具通过 `tool_search` + `call_mcp_tool` 两个"元工具"间接调用，LLM 实际执行的是 `call_mcp_tool(tool_name="xxx", arguments={...})`，参数是自由 dict，缺乏 JSON Schema 约束，导致参数准确率低、调试困难。同时只支持 Streamable HTTP 传输协议，部分未改造的 MCP 服务（SSE 协议）无法接入。

## What Changes

- 将 MCP 工具从"元工具间接调用"改为 pydantic-ai 原生 `Tool` 对象，每个 MCP 工具带完整 JSON Schema，LLM 直接 function calling
- 移除 `tool_search` 和 `call_mcp_tool` 两个元工具，移除 `DeferredToolRegistry` 渐进式加载机制
- 移除 System Prompt 中的 `<available_mcp_tools>` 文本注入，改由 pydantic-ai 工具列表自动暴露
- `MCPEndpointConfig` 新增 `transport` 字段（`sse` / `streamable`），支持 SSE 和 Streamable HTTP 两种传输协议
- `MCPClientManager` 改造：connect 时根据 transport 类型选择 `SSETransport` 或 `StreamableHttpTransport`，工具发现后包装为 pydantic-ai `Tool` 列表
- 保留自建连接管理层（多端点、定期刷新、原子替换、连接容错）

## Non-goals

- 不迁移到 pydantic-ai/pydantic-deep 原生 MCP capability（保留自建连接管理的灵活性）
- 不支持 stdio 传输协议（当前场景为远程 MCP 服务）
- 不改变前端 ToolResultCard 的 MCP 工具结果渲染逻辑

## Capabilities

### New Capabilities

- `mcp-native-tools`: MCP 工具动态包装为 pydantic-ai 原生 Tool，支持 SSE/Streamable 双协议传输

### Modified Capabilities

- `toolset-assembler`: MCP 工具不再通过 deferred_tool_names 注入 prompt，改为直接加入 agent tools 列表

## Impact

- 核心改动文件：`capabilities/mcp/client_manager.py`、`capabilities/base_tools.py`、`capabilities/registry.py`、`orchestrator/reasoning_engine.py`、`context/builder.py`
- 删除文件：`capabilities/mcp/deferred_registry.py`
- 配置变更：`MCPSettings` / `MCP_SERVERS` JSON 格式新增 `transport` 字段（默认 `streamable`，向后兼容）
- 依赖：fastmcp >= 3.1.1（已满足，内置 SSETransport + StreamableHttpTransport）
