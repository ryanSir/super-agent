## ADDED Requirements

### Requirement: MCP 工具调用开始时推送 tool_call 事件
当 pydantic-ai Agent 开始调用 MCP 工具时，系统 SHALL 通过 SSE 推送 `tool_call` 事件，包含工具名称，用于前端展示 loading 状态。

#### Scenario: MCP 工具开始调用
- **WHEN** pydantic-ai Agent 发出 MCP 工具调用（`ToolCallPart` 事件）
- **THEN** 系统推送 `{"event_type": "tool_call", "tool_name": "<name>", "tool_type": "mcp"}` 到 SSE 流

#### Scenario: 同一轮多个 MCP 工具并发调用
- **WHEN** Agent 在同一轮响应中调用多个 MCP 工具
- **THEN** 每个工具分别推送独立的 `tool_call` 事件，`tool_name` 各不相同

### Requirement: MCP 工具执行完成后推送 tool_result 事件
当 MCP 工具执行完成后，系统 SHALL 通过 SSE 推送 `tool_result` 事件，包含工具名称、执行结果内容和状态。

#### Scenario: MCP 工具执行成功
- **WHEN** pydantic-ai Agent 收到 MCP 工具返回结果（`ToolReturnPart` 事件）
- **THEN** 系统推送 `{"event_type": "tool_result", "tool_type": "mcp", "tool_name": "<name>", "content": "<result>", "status": "success"}` 到 SSE 流

#### Scenario: MCP 工具执行失败（ToolRetryError）
- **WHEN** MCP 工具调用抛出异常或返回错误
- **THEN** 系统推送 `{"event_type": "tool_result", "tool_type": "mcp", "tool_name": "<name>", "content": "<error_msg>", "status": "failed"}` 到 SSE 流

#### Scenario: content 为非字符串类型
- **WHEN** `ToolReturnPart.content` 为非字符串类型（dict、list 等）
- **THEN** 系统 SHALL 对 content 做 `str()` 转换后推送，不抛出异常

### Requirement: MCP fallback 时保持事件推送
当 MCP 连接失败降级为无 MCP 模式时，系统 SHALL 正常完成请求，不推送任何 MCP tool_call / tool_result 事件。

#### Scenario: MCP 连接超时降级
- **WHEN** `agent.run_stream()` 因 MCP 连接失败抛出异常，且 toolsets 非空
- **THEN** 系统降级为无 MCP 模式重新执行，不推送 MCP 相关事件
