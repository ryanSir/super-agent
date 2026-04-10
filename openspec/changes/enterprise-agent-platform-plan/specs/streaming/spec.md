## MODIFIED Requirements

### Requirement: WebSocket 双向通道
系统 SHALL 在现有 SSE 基础上增加 WebSocket 双向通道，用于 ask_clarification 用户回复、实时编辑协作、A2UI 交互事件回传等需要客户端主动推送的场景。

#### Scenario: 澄清回复
- **WHEN** Agent 推送 clarification_needed 事件
- **THEN** 用户 SHALL 通过 WebSocket 发送回复，Agent 从暂停点继续

#### Scenario: SSE + WebSocket 共存
- **WHEN** 客户端同时建立 SSE 和 WebSocket 连接
- **THEN** Agent 输出通过 SSE 推送，用户交互通过 WebSocket 发送，两者共享 session

### Requirement: 事件协议标准化
系统 SHALL 定义标准化的事件协议，所有事件 SHALL 包含：event_id（全局唯一）、event_type、session_id、timestamp、payload。事件类型 SHALL 使用枚举定义。

#### Scenario: 事件格式
- **WHEN** 系统推送任何事件
- **THEN** 事件 SHALL 符合标准格式：{"event_id": "uuid", "event_type": "token_delta", "session_id": "...", "timestamp": "ISO8601", "payload": {...}}

#### Scenario: 事件类型枚举
- **WHEN** 新增事件类型
- **THEN** SHALL 在 StreamEventType 枚举中注册，包含：session_created / token_delta / tool_call_start / tool_call_end / clarification_needed / mode_escalated / todo_updated / file_changed / session_completed / session_failed

### Requirement: 断点续传完善
系统 SHALL 完善断点续传机制，支持 Last-Event-ID 精确恢复、事件缓冲窗口（默认保留最近 1000 条事件）、过期事件清理。

#### Scenario: 精确恢复
- **WHEN** 客户端携带 Last-Event-ID 重连
- **THEN** 系统 SHALL 从该 event_id 之后的事件开始推送，不丢失不重复

#### Scenario: 缓冲窗口溢出
- **WHEN** 客户端断线时间过长，Last-Event-ID 对应的事件已被清理
- **THEN** 系统 SHALL 返回 409 Conflict，客户端需要重新建立会话
