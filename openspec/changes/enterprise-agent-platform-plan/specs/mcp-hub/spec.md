## ADDED Requirements

### Requirement: MCP Client 双协议连接
系统 SHALL 支持 stdio 和 SSE 两种 MCP 传输协议。stdio 用于本地进程通信，SSE 用于远程服务连接。连接 SHALL 支持自动重连和健康检查。

#### Scenario: stdio 连接
- **WHEN** MCP 配置指定 transport=stdio 和可执行文件路径
- **THEN** 系统 SHALL 启动子进程，通过 stdin/stdout 进行 JSON-RPC 通信

#### Scenario: SSE 连接
- **WHEN** MCP 配置指定 transport=sse 和远程 URL
- **THEN** 系统 SHALL 建立 SSE 连接，通过 HTTP POST 发送请求

#### Scenario: 连接断开自动重连
- **WHEN** MCP 连接意外断开
- **THEN** 系统 SHALL 在 5 秒内尝试重连，最多重试 3 次，失败后标记该 MCP 服务不可用

### Requirement: 工具聚合与自动发现
系统 SHALL 聚合所有 MCP 服务暴露的工具，统一注册到 CapabilityRegistry。新 MCP 服务上线时 SHALL 自动发现并注册其工具。

#### Scenario: 多 MCP 工具聚合
- **WHEN** 连接了 3 个 MCP 服务，分别暴露 5/3/7 个工具
- **THEN** CapabilityRegistry SHALL 包含全部 15 个工具，工具名称 SHALL 带 MCP 服务前缀避免冲突

#### Scenario: 工具名称冲突
- **WHEN** 两个 MCP 服务暴露了同名工具
- **THEN** 系统 SHALL 使用 "{service_name}:{tool_name}" 格式区分

#### Scenario: MCP 服务下线
- **WHEN** 某个 MCP 服务不可用
- **THEN** 系统 SHALL 将其工具标记为不可用，Agent 调用时返回友好错误

### Requirement: DeferredToolRegistry 渐进式加载
系统 SHALL 实现 MCP 工具的渐进式加载：启动时只注册工具名称和描述到 prompt，Agent 需要时通过 tool_search 获取完整 Schema 后再调用。

#### Scenario: 启动时注入名称
- **WHEN** 系统启动并连接 MCP 服务
- **THEN** System Prompt 的 <available_deferred_tools> 段落 SHALL 只包含工具名称列表，不包含完整 Schema

#### Scenario: 按需加载 Schema
- **WHEN** Agent 调用 tool_search("select:slack_send")
- **THEN** 系统 SHALL 从 MCP 服务获取 slack_send 的完整 JSON Schema 并返回给 Agent

#### Scenario: Schema 缓存
- **WHEN** 同一工具的 Schema 被多次请求
- **THEN** 系统 SHALL 使用缓存，不重复请求 MCP 服务

### Requirement: MCP Server 暴露能力
系统 SHALL 实现 MCP Server，将平台内置工具暴露给外部客户端（Cursor / Claude Desktop / 其他 MCP Client）。

#### Scenario: 外部客户端连接
- **WHEN** Cursor 通过 MCP 协议连接到本系统
- **THEN** 系统 SHALL 返回可用工具列表（RAG 检索、DB 查询、Skill 执行等）

#### Scenario: 外部工具调用
- **WHEN** 外部客户端调用 execute_rag_search 工具
- **THEN** 系统 SHALL 执行 RAG 检索并返回结果，格式符合 MCP 协议规范
