## MODIFIED Requirements

### Requirement: SSE 事件类型

所有事件通过 `publish_event(session_id, event_dict)` 发布到 Redis Stream，前端通过 SSE 订阅 `GET /stream/{session_id}`。

系统 MUST 支持以下事件类型：

| event_type | 触发时机 | 关键字段 |
|-----------|---------|---------|
| `step` | 任务开始/完成/失败 | `step_id`, `title`, `status` (running/completed/failed), `detail` |
| `tool_result` | Worker/Skill/Tool 执行完成 | `tool_type`, `tool_name`, `content`, `status` |
| `render_widget` | Agent 调用 emit_chart/emit_widget | `widget_id`, `ui_component`, `props` |
| `text_stream` | LLM 流式输出 | `delta`, `is_final` |
| `process_update` | 进度更新 | `phase`, `status`, `message`, `progress` |
| `tool_call` | Agent 发起工具调用（调用前） | `tool_name`, `args` |
| `session_completed` | 编排完成 | `answer` |
| `session_failed` | 编排失败 | `error` |
| `session_created` | 会话创建 | `session_id` |
| `memory_update` | 记忆系统更新完成 | `user_id`, `update_type` (profile/fact), `summary` |
| `middleware_event` | Middleware 产生的中间事件 | `middleware_name`, `event_subtype`, `detail` |

#### Scenario: text_stream 事件流式推送
- **WHEN** LLM 生成文本回答
- **THEN** 系统 MUST 通过 `text_stream` 事件推送增量文本，每个事件包含 `delta`（增量文本）和 `is_final`（是否结束）

#### Scenario: tool_call 和 tool_result 配对
- **WHEN** Agent 调用工具
- **THEN** 系统 MUST 先推送 `tool_call` 事件（包含 tool_name 和 args），工具执行完成后推送 `tool_result` 事件（包含 content 和 status）

#### Scenario: render_widget 事件推送
- **WHEN** Agent 调用 `emit_chart` 工具且返回成功
- **THEN** 系统 MUST 推送 `render_widget` 事件，`ui_component` 字段映射到前端 ComponentRegistry

#### Scenario: session_completed 包含完整回答
- **WHEN** Agent 执行完成
- **THEN** 系统 MUST 推送 `session_completed` 事件，`answer` 字段包含 LLM 的完整文本回答（非空）
