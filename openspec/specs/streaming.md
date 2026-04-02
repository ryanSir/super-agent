# Streaming 规格

## 架构

系统支持两种实时通信通道：

| 通道 | 文件 | 用途 |
|------|------|------|
| SSE | `src/streaming/sse_endpoint.py` | 服务端 → 客户端单向推送（主通道） |
| WebSocket | `src/gateway/websocket_api.py` | 双向通信 |
| 事件队列 | `src/streaming/stream_adapter.py` | 内部事件分发（asyncio.Queue） |

## SSE 端点

```python
def create_sse_response(
    session_id: str,
    last_event_id: str = "0-0",  # 支持断点续传
) -> EventSourceResponse
```

- 基于 `sse-starlette` 库
- 每个事件包含 `event: message`、`id: <event_id>`、`data: <json>`
- 支持 `Last-Event-ID` 请求头断点续传

## 事件流格式

所有事件通过 `publish_event(session_id, event_dict)` 发布到 Redis Stream，
前端通过 SSE 订阅 `GET /stream/{session_id}`。

### 事件类型

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

### Requirement: Temporal 工作流状态事件
系统 SHALL 在工作流提交和完成时推送状态事件到 Redis Streams，使客户端可通过 SSE 感知 Temporal 执行状态。

#### Scenario: 工作流提交成功事件
- **WHEN** `submit_orchestrator_workflow()` 成功提交工作流到 Temporal
- **THEN** 系统 MUST 推送 `workflow_submitted` 事件，包含 `workflow_id` 和 `run_id` 字段

#### Scenario: Temporal 降级为直接执行
- **WHEN** Temporal 不可用，系统降级为直接 `asyncio.create_task` 执行
- **THEN** 系统 MUST 推送 `workflow_fallback` 事件，`detail` 字段说明降级原因，后续事件流与正常路径一致

#### Scenario: 前端忽略未知 Temporal 事件
- **WHEN** 前端收到 `workflow_submitted` 或 `workflow_fallback` 事件
- **THEN** 前端 MUST 忽略或仅作日志记录，不影响正常 UI 渲染流程

### step 事件示例

```json
{
  "event_type": "step",
  "step_id": "plan",
  "title": "规划任务",
  "status": "running"
}
```

### tool_result 事件示例

```json
{
  "event_type": "tool_result",
  "tool_type": "skill",
  "tool_name": "paper-search",
  "content": "...",
  "status": "success"
}
```

## 关键约束

- 事件序列化使用 `json.dumps(ensure_ascii=False)`，datetime 转 ISO 格式字符串
- 每个 session 有独立的事件队列，通过 `session_id` 隔离
- SSE 连接断开后，客户端可通过 `Last-Event-ID` 从断点恢复
- 内部事件发布通过 `publish_event()` 统一入口，不直接操作 Redis
