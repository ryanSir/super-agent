### Requirement: ToolSetAssembler 装配接口
系统 SHALL 提供 `ToolSetAssembler` 类，根据 `ExecutionMode` 返回该模式下 Agent 可用的工具配置。MUST 位于 `src/orchestrator/toolset_assembler.py`。

#### Scenario: 获取 direct 模式工具集
- **WHEN** 调用 `assemble(ExecutionMode.DIRECT)`
- **THEN** 返回的工具配置中 MUST 排除 `plan_and_decompose`、`list_available_skills`、`create_new_skill`

#### Scenario: 获取 auto 模式工具集
- **WHEN** 调用 `assemble(ExecutionMode.AUTO)`
- **THEN** 返回全部工具，无任何过滤

#### Scenario: 获取 plan_and_execute 模式工具集
- **WHEN** 调用 `assemble(ExecutionMode.PLAN_AND_EXECUTE)`
- **THEN** 返回全部工具，且附带 prompt_prefix 强制先调用 plan_and_decompose

### Requirement: 工具过滤机制
ToolSetAssembler MUST 通过以下方式之一实现工具过滤：
1. 优先方案：利用 PydanticAI 的运行时工具过滤 API（如果支持）
2. 备选方案：为 direct 模式创建独立的 Agent 实例（lazy 初始化，共享 model 配置，工具列表不同）

无论哪种方案，MUST 保证 direct 模式下 Agent 无法调用 `plan_and_decompose`。

#### Scenario: direct 模式 Agent 尝试规划
- **WHEN** direct 模式下 LLM 试图调用 plan_and_decompose
- **THEN** 该工具不存在于可用工具列表中，LLM 被迫选择其他执行工具

#### Scenario: 工具过滤不影响 MCP 工具
- **WHEN** direct 模式下存在 MCP 外部工具
- **THEN** MCP 工具 MUST 不受过滤影响，正常可用

### Requirement: PromptPrefix 装配
ToolSetAssembler MUST 为 `plan_and_execute` 模式返回 `prompt_prefix` 字符串，内容为强制规划指引。`direct` 和 `auto` 模式的 `prompt_prefix` MUST 为空字符串。

#### Scenario: plan_and_execute 的 prompt_prefix
- **WHEN** 调用 `assemble(ExecutionMode.PLAN_AND_EXECUTE)`
- **THEN** 返回的 `prompt_prefix` 包含 "请先调用 plan_and_decompose 进行任务规划"

### Requirement: AssembleResult 数据结构
`assemble()` 方法 MUST 返回 `AssembleResult` 数据类，包含：
- `tool_filter`: 可选的工具名称黑名单列表
- `prompt_prefix`: 注入到 query 前的文本
- `agent_override`: 可选的替代 Agent 实例（用于 direct 模式备选方案）

#### Scenario: auto 模式返回空配置
- **WHEN** 调用 `assemble(ExecutionMode.AUTO)`
- **THEN** 返回 `AssembleResult(tool_filter=None, prompt_prefix="", agent_override=None)`
