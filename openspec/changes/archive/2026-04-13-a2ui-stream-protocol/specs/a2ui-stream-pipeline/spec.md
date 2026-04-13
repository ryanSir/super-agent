## ADDED Requirements

### Requirement: Agent 流式执行管道推送 A2UI 事件

系统 SHALL 在 `agent.iter()` 遍历执行节点时，将每种 PydanticAI node 类型映射为对应的 A2UI 事件帧，通过 SSE 实时推送到前端。

#### Scenario: LLM 文本流式输出
- **WHEN** `agent.iter()` 产出 `ModelRequestNode` 且模型返回文本内容
- **THEN** 系统 MUST 推送 `text_stream` 事件，`delta` 字段包含增量文本片段，`is_final=false`

#### Scenario: LLM 文本输出完成
- **WHEN** `agent.iter()` 产出 `End` 节点
- **THEN** 系统 MUST 推送 `text_stream` 事件，`is_final=true`，`delta` 为空字符串

#### Scenario: 工具调用结果推送
- **WHEN** `agent.iter()` 产出 `CallToolsNode` 且工具执行完成
- **THEN** 系统 MUST 推送 `tool_result` 事件，包含 `tool_name`、`status`（success/failed）、`content`（结果摘要，截取前 500 字符）

#### Scenario: emit_chart 工具触发 render_widget
- **WHEN** `CallToolsNode` 中 `tool_name` 为 `emit_chart` 且返回 `success=true`
- **THEN** 系统 MUST 额外推送 `render_widget` 事件，`ui_component="DataChart"`，`props` 包含图表配置，`widget_id` 格式为 `chart-{uuid8}`

#### Scenario: 阶段切换推送 process_update
- **WHEN** 编排流程从 planning 切换到 executing，或从 executing 切换到 completed/failed
- **THEN** 系统 MUST 推送 `process_update` 事件，`phase` 为当前阶段名，`status` 为 `in_progress`/`completed`/`failed`

### Requirement: 统一事件信封格式

所有 SSE 事件 SHALL 遵循统一的 JSON 信封格式，包含 `event_type`、`trace_id`、`session_id`、`timestamp` 四个公共字段。

#### Scenario: 事件包含完整信封
- **WHEN** 系统推送任意 A2UI 事件
- **THEN** 事件 JSON MUST 包含 `event_type`（字符串）、`trace_id`（字符串）、`session_id`（字符串）、`timestamp`（ISO 8601 格式）

#### Scenario: 未知事件类型前端静默忽略
- **WHEN** 前端收到未识别的 `event_type`
- **THEN** 前端 MUST 忽略该事件，不抛出错误

### Requirement: 流式管道超限优雅降级

系统 SHALL 在 `agent.iter()` 超出 `request_limit` 时，从已有消息历史中提取最后一条文本回答，而非直接报错。

#### Scenario: 请求次数超限降级
- **WHEN** `agent.iter()` 抛出 `UsageLimitExceeded` 异常
- **THEN** 系统 MUST 从消息历史中提取最后一条文本内容作为回答，推送 `text_stream(is_final=true)` 和 `session_completed` 事件

#### Scenario: 消息历史为空时超限
- **WHEN** `agent.iter()` 超限且消息历史中无文本内容
- **THEN** 系统 MUST 推送 `session_failed` 事件，`error` 字段说明超限原因

### Requirement: text_stream 事件批量合并

系统 SHALL 对高频 `text_stream` 事件进行批量合并，避免 Redis Stream 写入压力过大。

#### Scenario: 200ms 内多个 delta 合并
- **WHEN** 200ms 内产生多个 `text_stream` delta
- **THEN** 系统 SHOULD 将多个 delta 合并为一个事件推送，`delta` 字段为拼接后的文本

#### Scenario: 超过 200ms 无新 delta
- **WHEN** 距上次 delta 超过 200ms
- **THEN** 系统 MUST 立即推送已缓冲的 delta
