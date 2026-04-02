## MODIFIED Requirements

### Requirement: 事件类型
所有事件通过 `publish_event(session_id, event_dict)` 发布到 Redis Stream，前端通过 SSE 订阅 `GET /stream/{session_id}`。

系统 MUST 支持以下事件类型：

| event_type | 触发时机 | 关键字段 |
|-----------|---------|---------|
| `step` | 任务开始/完成/失败 | `step_id`, `title`, `status` (running/completed/failed), `detail` |
| `tool_result` | Worker/Skill 执行完成 | `tool_type`, `tool_name`, `content`, `status` |
| `render_widget` | Orchestrator 调用 emit_chart/emit_widget | `widget_id`, `ui_component`, `props` |
| `text_stream` | LLM 流式输出 | `delta`, `is_final` |
| `process_update` | 进度更新 | `phase`, `status`, `message`, `progress` |
| `memory_update` | 记忆系统更新完成 | `user_id`, `update_type` (profile/fact), `summary` |
| `middleware_event` | Middleware 产生的中间事件 | `middleware_name`, `event_subtype`, `detail` |

#### Scenario: 记忆更新事件
- **WHEN** MemoryUpdater 完成一次记忆更新
- **THEN** 发布 `memory_update` 事件，包含 `user_id`、`update_type`（"profile" 或 "fact"）、`summary`（更新摘要）

#### Scenario: 循环检测警告事件
- **WHEN** LoopDetectionMiddleware 检测到重复 tool 调用并注入警告
- **THEN** 发布 `middleware_event` 事件，`middleware_name="loop_detection"`，`event_subtype="warning"`，`detail` 包含重复的 tool 名称

#### Scenario: 循环检测强制终止事件
- **WHEN** LoopDetectionMiddleware 触发强制终止
- **THEN** 发布 `middleware_event` 事件，`middleware_name="loop_detection"`，`event_subtype="hard_stop"`

#### Scenario: token 用量事件
- **WHEN** TokenUsageMiddleware 记录 token 用量
- **THEN** 发布 `middleware_event` 事件，`middleware_name="token_usage"`，`event_subtype="usage_report"`，`detail` 包含 input/output/total token 数

#### Scenario: 前端忽略未知事件类型
- **WHEN** 前端收到未识别的 event_type
- **THEN** 前端 MUST 忽略该事件，不抛出错误（向后兼容）
