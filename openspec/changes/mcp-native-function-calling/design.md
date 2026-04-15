## Context

当前 MCP 工具通过 `DeferredToolRegistry` 渐进式加载，Agent 需要先调用 `tool_search` 获取 schema，再调用 `call_mcp_tool` 间接执行。这种"元工具"模式缺乏 JSON Schema 约束，参数准确率依赖 LLM 自行理解文本描述。

同时，`MCPClientManager` 使用 `fastmcp.client.Client(url)` 连接，默认走 Streamable HTTP 协议。部分未改造的 MCP 服务仍使用 SSE 协议，当前无法接入。

fastmcp 3.1.1 已内置 `SSETransport` 和 `StreamableHttpTransport`，pydantic-ai 1.70.0 支持动态注册 `Tool` 对象。

## Goals / Non-Goals

**Goals:**
- MCP 工具以 pydantic-ai 原生 `Tool` 形式注入 Agent，LLM 直接 function calling，带完整 JSON Schema
- 支持 SSE 和 Streamable HTTP 两种 MCP 传输协议，通过配置切换
- 保留自建连接管理层（多端点、定期刷新、原子替换、容错降级）

**Non-Goals:**
- 不迁移到 pydantic-deep 原生 MCP capability
- 不支持 stdio 传输协议
- 不改变前端渲染逻辑

## Decisions

### Decision 1: MCP 工具包装为 pydantic-ai Tool

**选择**: MCPClientManager 发现工具后，为每个 MCP 工具动态创建 `pydantic_ai.Tool` 对象，包含完整 `parameters_json_schema`，通过闭包绑定 `call_tool` 执行逻辑。

**替代方案**: 保留 `call_mcp_tool` 元工具但注入完整 schema 到 prompt → 仍然是文本约束而非结构化约束，LLM 可能忽略。

**理由**: 原生 Tool 让 LLM 在 function calling 层面就有参数类型和必填校验，不依赖 prompt 理解。

**实现要点**:
```python
from pydantic_ai import Tool

def _wrap_mcp_tool(tool_name: str, description: str, schema: dict, server_name: str) -> Tool:
    """将单个 MCP 工具包装为 pydantic-ai Tool"""
    async def _caller(ctx: RunContext[Any], **kwargs: Any) -> dict[str, Any]:
        return await mcp_client_manager.call_tool(tool_name, kwargs)

    return Tool(
        function=_caller,
        name=tool_name,
        description=description,
        parameters_json_schema=schema,
    )
```

MCPClientManager 新增 `get_tools() -> list[Tool]` 方法，返回所有已发现工具的 Tool 列表。

### Decision 2: 传输协议选择策略

**选择**: `MCPEndpointConfig` 新增 `transport` 字段，值为 `"sse"` 或 `"streamable"`（默认），connect 时根据该字段选择 transport 类。

**替代方案 A**: 自动探测（先尝试 streamable，失败回退 sse）→ 增加连接延迟，且探测逻辑脆弱。

**替代方案 B**: 通过 URL 后缀区分（如 `/sse` vs `/mcp`）→ 不可靠，URL 命名无标准。

**理由**: 显式配置最可靠，运维人员清楚自己的 MCP 服务用什么协议。

**配置格式**:
```json
[
  {"name": "tools", "url": "http://localhost:3000/mcp", "transport": "streamable"},
  {"name": "legacy", "url": "http://localhost:3001/sse", "transport": "sse"}
]
```

**实现要点**:
```python
from fastmcp.client.transports import SSETransport, StreamableHttpTransport

def _create_transport(ep: MCPEndpointConfig):
    if ep.transport == "sse":
        return SSETransport(url=ep.url, headers=ep.headers)
    return StreamableHttpTransport(url=ep.url, headers=ep.headers)
```

### Decision 3: 工具注入方式

**选择**: 移除 `DeferredToolRegistry` 和 System Prompt 中的 `<available_mcp_tools>` 文本注入。MCP 工具通过 `CapabilityRegistry.get_agent_tools()` 返回，与 base_tools 合并后传入 Agent。

**理由**: pydantic-ai 的 Tool 列表自动暴露给 LLM，无需额外 prompt 注入。减少 prompt token 消耗，消除文本描述与实际 schema 不一致的风险。

### Decision 4: 刷新时工具列表热替换

**选择**: 刷新时重新构建 `list[Tool]`，通过原子替换 `_tools` 引用。下次 Agent 执行时自动使用新列表。

**理由**: 保持现有的原子替换策略，避免刷新期间的空窗口。正在执行的 Agent 不受影响（已持有旧引用），新请求使用新工具列表。

## Risks / Trade-offs

**[工具数量膨胀]** → 如果 MCP 端点暴露大量工具（50+），全量注入 Agent tools 列表会增加 prompt token。
→ 缓解：当前场景工具数量可控（<30）。未来如需优化，可在 MCPClientManager 层做工具白名单过滤。

**[刷新期间 Tool 引用不一致]** → 刷新替换 tools 列表后，正在执行的 Agent 仍持有旧 Tool 闭包，闭包内的 `call_tool` 指向旧的 tool_name 映射。
→ 缓解：`call_tool` 通过 `_tool_to_server` 查找，刷新时同步替换该映射，闭包调用时使用最新映射。

**[SSE 协议兼容性]** → 部分 SSE 服务可能有非标准实现。
→ 缓解：fastmcp SSETransport 遵循 MCP 规范，非标准服务需自行适配。连接失败时跳过该端点，不影响其他端点。

**[向后兼容]** → `MCP_SERVERS` JSON 格式新增 `transport` 字段。
→ 缓解：默认值为 `"streamable"`，不配置 transport 字段时行为与改造前一致。
