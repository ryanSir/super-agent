## ADDED Requirements

### Requirement: EventPublishingCapability 统一事件发布
系统 SHALL 提供 `EventPublishingCapability`（继承 `AbstractCapability`），作为所有 Agent 运行时事件发布的唯一出口。该 Capability MUST 通过 pydantic-ai 生命周期方法（`wrap_tool_execute`、`after_model_request`、`after_run`）拦截事件，并通过注入的 `publish_fn` 发布到 Redis Stream。

#### Scenario: 工具调用事件发布
- **WHEN** Agent 调用任意工具（包括自定义工具和框架内置工具）
- **THEN** Capability MUST 在工具执行前发布 `tool_call` 事件（包含 tool_name、tool_type、args），在工具执行后发布 `tool_result` 事件（包含 tool_name、tool_type、status、content）

#### Scenario: emit_chart 工具的 render_widget 事件
- **WHEN** Agent 调用 `emit_chart` 工具且执行成功
- **THEN** Capability MUST 额外发布 `render_widget` 事件（包含 widget_id、ui_component、props），格式与当前 `_handle_emit_chart_result` 输出一致

#### Scenario: LLM 响应中的 thinking 事件
- **WHEN** LLM 响应包含 `thinking` 类型的 part
- **THEN** Capability MUST 在 `after_model_request` 中发布 `thinking` 事件（包含 content）

#### Scenario: LLM 响应中的文本流事件
- **WHEN** LLM 响应包含文本内容的 part
- **THEN** Capability MUST 发布 `text_stream` 事件（包含 delta、is_final=false）

#### Scenario: Agent 运行结束的流终止标记
- **WHEN** Agent run 正常完成
- **THEN** Capability MUST 在 `after_run` 中发布 `text_stream` 事件（delta=""、is_final=true）

#### Scenario: 工具执行失败的事件发布
- **WHEN** 工具执行抛出异常
- **THEN** Capability MUST 在 `on_tool_execute_error` 中发布 `tool_result` 事件（status="error"、content 包含异常摘要，截断至 500 字符）

#### Scenario: publish_fn 为 None 时静默跳过
- **WHEN** `EventPublishingCapability` 的 `publish_fn` 为 None
- **THEN** 所有事件发布操作 MUST 静默跳过，不抛出异常

#### Scenario: 并发工具调用的事件去重
- **WHEN** 同一 run 中多个工具并发执行
- **THEN** Capability MUST 通过 `_reported_tool_ids` 集合确保每个 tool_call_id 只发布一次 tool_result

### Requirement: Langfuse Tracing 集成
`EventPublishingCapability` SHALL 在 `wrap_tool_execute` 中为每次工具调用创建 Langfuse trace span，记录工具名、参数、耗时、结果状态。

#### Scenario: 正常工具调用的 span 记录
- **WHEN** 工具执行成功
- **THEN** Capability MUST 创建 span（name=`tool_{name}`、type=tool），记录 input（参数）和 output（结果）

#### Scenario: 工具执行失败的 span 记录
- **WHEN** 工具执行抛出异常
- **THEN** Capability MUST 更新 span 的 level 为 ERROR，status_message 包含异常摘要

#### Scenario: Langfuse 未启用时降级
- **WHEN** Langfuse 配置 `enabled=false`
- **THEN** trace span 操作 MUST 为 no-op，不影响工具执行

### Requirement: EventPublishingCapability 通过配置开关控制
系统 SHALL 通过 `EVENT_PUBLISHING_ENABLED` 环境变量控制 `EventPublishingCapability` 是否注册到 Agent。

#### Scenario: 默认启用
- **WHEN** 未设置 `EVENT_PUBLISHING_ENABLED` 环境变量
- **THEN** 默认值为 `true`，Capability 正常注册

#### Scenario: 显式禁用
- **WHEN** 设置 `EVENT_PUBLISHING_ENABLED=false`
- **THEN** `create_orchestrator_agent` MUST 不注册 `EventPublishingCapability`，事件不发布
