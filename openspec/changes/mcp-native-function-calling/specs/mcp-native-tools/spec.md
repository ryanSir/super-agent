## ADDED Requirements

### Requirement: MCP 工具包装为 pydantic-ai 原生 Tool
MCPClientManager 发现工具后，SHALL 为每个 MCP 工具创建 `pydantic_ai.Tool` 对象，包含工具名称、描述和完整 `parameters_json_schema`。Agent 执行时 MUST 通过标准 function calling 调用 MCP 工具，而非元工具间接调用。

#### Scenario: 单端点工具发现与包装
- **WHEN** MCPClientManager 连接到一个包含 3 个工具的 MCP 端点
- **THEN** `get_tools()` 返回 3 个 `pydantic_ai.Tool` 对象，每个包含对应的 name、description 和 parameters_json_schema

#### Scenario: 多端点工具合并
- **WHEN** MCPClientManager 连接到 2 个端点，分别有 3 和 2 个工具
- **THEN** `get_tools()` 返回 5 个 Tool 对象（无名称冲突时）

#### Scenario: 工具名冲突自动加前缀
- **WHEN** 两个端点都暴露名为 `search` 的工具，端点名分别为 `github` 和 `slack`
- **THEN** 第二个发现的工具 MUST 重命名为 `slack:search`，两个工具均可独立调用

#### Scenario: Tool 闭包执行
- **WHEN** LLM 通过 function calling 调用某个 MCP Tool，传入参数 `{"channel": "general", "text": "hello"}`
- **THEN** Tool 闭包 MUST 调用 `MCPClientManager.call_tool(tool_name, arguments)` 并返回执行结果

### Requirement: SSE 和 Streamable HTTP 双协议支持
MCPClientManager SHALL 支持 SSE 和 Streamable HTTP 两种 MCP 传输协议。端点配置中 MUST 包含 `transport` 字段，值为 `"sse"` 或 `"streamable"`，默认为 `"streamable"`。

#### Scenario: Streamable HTTP 端点连接（默认）
- **WHEN** 端点配置未指定 transport 或 transport 为 `"streamable"`
- **THEN** MUST 使用 `StreamableHttpTransport` 建立连接

#### Scenario: SSE 端点连接
- **WHEN** 端点配置 transport 为 `"sse"`
- **THEN** MUST 使用 `SSETransport` 建立连接

#### Scenario: 无效 transport 值
- **WHEN** 端点配置 transport 为不支持的值（如 `"stdio"`）
- **THEN** MUST 记录 warning 日志并跳过该端点，不影响其他端点连接

#### Scenario: 混合协议多端点
- **WHEN** 配置 2 个端点，一个 SSE 一个 Streamable
- **THEN** 两个端点 MUST 各自使用对应的 transport 独立连接，工具合并到同一个 tools 列表

### Requirement: 移除元工具间接调用
系统 SHALL 移除 `tool_search` 和 `call_mcp_tool` 两个元工具函数。MCP 工具 MUST 仅通过 pydantic-ai 原生 function calling 调用。

#### Scenario: Agent 工具列表不包含元工具
- **WHEN** Agent 初始化时获取工具列表
- **THEN** 工具列表中 MUST 不包含 `tool_search` 和 `call_mcp_tool`

#### Scenario: Agent 直接调用 MCP 工具
- **WHEN** Agent 需要调用名为 `slack_send` 的 MCP 工具
- **THEN** LLM 直接生成 `slack_send(channel="general", text="hello")` function call，而非 `call_mcp_tool(tool_name="slack_send", arguments={...})`

### Requirement: 移除 DeferredToolRegistry
系统 SHALL 移除 `DeferredToolRegistry` 及其渐进式加载机制。MCP 工具的 schema 在连接时一次性获取并包装为 Tool 对象。

#### Scenario: 启动时全量加载
- **WHEN** MCPClientManager.connect() 完成
- **THEN** 所有工具的完整 schema MUST 已包含在 Tool 对象中，无需后续按需加载

### Requirement: 定期刷新工具列表
MCPClientManager SHALL 保留定期刷新机制。刷新时 MUST 重新发现工具、重新包装为 Tool 对象、原子替换工具列表。

#### Scenario: 刷新成功
- **WHEN** 定期刷新触发，所有端点正常响应
- **THEN** `get_tools()` 返回新的 Tool 列表，旧列表引用不受影响

#### Scenario: 部分端点刷新失败
- **WHEN** 刷新时 1 个端点超时，其余正常
- **THEN** MUST 保留正常端点的新工具，超时端点的旧工具被移除，记录 error 日志

#### Scenario: 全部端点刷新失败
- **WHEN** 刷新时所有端点均失败
- **THEN** MUST 保留旧工具列表不变，记录 error 日志

### Requirement: 连接容错
MCPClientManager SHALL 在连接阶段对单个端点失败进行容错处理。

#### Scenario: 单端点连接失败
- **WHEN** 连接 3 个端点时，第 2 个端点超时
- **THEN** MUST 跳过该端点，继续连接第 3 个端点，最终返回成功连接的端点工具

#### Scenario: 连接超时
- **WHEN** 端点在 `MCP_CONNECT_TIMEOUT` 秒内未响应
- **THEN** MUST 标记该端点连接失败并跳过
