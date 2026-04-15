## MODIFIED Requirements

### Requirement: 工具过滤不影响 MCP 工具
ToolSetAssembler 在过滤工具时，MCP 工具 MUST 不受过滤影响。MCP 工具不再通过 `deferred_tool_names` 注入 System Prompt，而是作为 pydantic-ai Tool 对象加入 Agent 工具列表，与 base_tools 统一管理。

#### Scenario: direct 模式下 MCP 工具可用
- **WHEN** direct 模式下存在 MCP 外部工具
- **THEN** MCP 工具 MUST 出现在 Agent 的 tools 列表中，可通过 function calling 直接调用

#### Scenario: MCP 工具不再通过 prompt 注入
- **WHEN** 构建 System Prompt 时
- **THEN** MUST 不包含 `<available_mcp_tools>` 段落，MCP 工具信息由 pydantic-ai 工具列表自动暴露给 LLM
