## ADDED Requirements

### Requirement: 支持多 MCP 端点配置
系统 SHALL 支持通过 `MCP_SERVERS` 环境变量配置多个命名 MCP 端点，每个端点包含 name、url 和可选 headers 字段。

#### Scenario: 多端点正常加载
- **WHEN** `MCP_SERVERS` 配置为合法 JSON 数组（如 `[{"name":"tools","url":"http://a/mcp"},{"name":"search","url":"http://b/mcp"}]`）
- **THEN** 系统 SHALL 为每个端点创建独立的 `MCPServerStreamableHTTP` 实例并注入 Orchestrator Agent

#### Scenario: 回退到单端点
- **WHEN** `MCP_SERVERS` 未配置，但 `MCP_SERVER_URL` 已配置
- **THEN** 系统 SHALL 创建名为 `default` 的单个 MCP server，行为与原来一致

#### Scenario: JSON 解析失败
- **WHEN** `MCP_SERVERS` 值不是合法 JSON
- **THEN** 系统 SHALL 记录 warning 日志并回退到 `MCP_SERVER_URL` 单端点行为，不抛出异常阻断启动

#### Scenario: 单个端点不可达
- **WHEN** 多端点配置中某个 url 无法连接
- **THEN** 系统 SHALL 跳过该端点并记录 error 日志，其余端点正常注入

#### Scenario: 端点名称重复
- **WHEN** `MCP_SERVERS` 中存在两个相同 name 的端点
- **THEN** 系统 SHALL 以最后一个配置为准，并记录 warning 日志
