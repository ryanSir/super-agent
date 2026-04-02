## ADDED Requirements

### Requirement: tool_call 事件类型
系统 SHALL 支持 `tool_call` 事件类型，在工具开始调用时推送，用于前端展示 loading 状态。

#### Scenario: 前端收到 tool_call 事件
- **WHEN** 前端 SSE 收到 `event_type: "tool_call"` 事件
- **THEN** 前端 MUST 在对应工具结果卡片位置展示 loading 占位，不抛出错误

#### Scenario: 前端收到未知 tool_call 工具名
- **WHEN** `tool_call` 事件中 `tool_name` 不在已知图标映射中
- **THEN** 前端 MUST 使用默认图标展示，不抛出错误
