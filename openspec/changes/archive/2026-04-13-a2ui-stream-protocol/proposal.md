## Why

当前 Agent 执行流程中，SSE 事件流只推送了 `session_created`、`tool_call`、`session_completed` 三种粗粒度事件，缺少 A2UI 规范中定义的 `text_stream`（LLM 流式输出）、`render_widget`（图表/组件渲染）、`process_update`（进度更新）等关键事件类型。导致前端无法实时展示 LLM 回答文本、无法渲染图表组件、无法显示执行进度。需要将 A2UI 协议完整落地到 `agent.iter()` 流式执行管道中。

## What Changes

- 定义统一的 SSE 事件数据格式，所有事件遵循 `A2UIFrame` 基类结构（`event_type` + `trace_id` + `timestamp` + payload）
- 在 `_execute_plan` 的 `agent.iter()` 循环中，按节点类型推送对应的 A2UI 事件：
  - `ModelRequestNode` → 流式推送 `text_stream` 事件（delta 增量文本）
  - `CallToolsNode` → 推送 `tool_result` 事件（工具名、参数、结果摘要）
  - `emit_chart` / `emit_widget` 工具返回值 → 推送 `render_widget` 事件
  - 阶段切换 → 推送 `process_update` 事件（planning → executing → completed）
- `emit_chart` 工具改造：返回值中包含完整的 `RenderWidget` 帧，由流式管道统一推送到 SSE
- 前端 `MessageHandler.ts` 按 `event_type` 分发渲染，未知类型静默忽略

## Non-goals

- 不改造 WebSocket 双向通道，本次只聚焦 SSE 单向推送
- 不新增前端组件类型，复用现有 `DataChart`、`ArtifactPreview`、`TerminalView`、`ProcessUI`
- 不引入消息持久化或回放机制，事件仍通过 Redis Stream 短期存储

## Capabilities

### New Capabilities
- `a2ui-stream-pipeline`: Agent 流式执行管道与 A2UI 事件推送的完整集成，包括 text_stream、render_widget、tool_result、process_update 事件的生成和推送

### Modified Capabilities
- `streaming`: 扩展现有 SSE 事件流，补充 `text_stream` 和 `render_widget` 事件类型的实际推送逻辑
- `a2ui-protocol`: 将 A2UI 帧定义从 spec 落地到 `src_deepagent/schemas/` 中，确保后端实际使用

## Impact

- `src_deepagent/gateway/rest_api.py` — `_execute_plan` 流式管道重构
- `src_deepagent/capabilities/base_tools.py` — `emit_chart` 返回值格式调整
- `src_deepagent/schemas/` — 新增 `a2ui.py` 数据模型
- `src_deepagent/streaming/stream_adapter.py` — 事件发布接口适配 A2UI 帧
- `frontend-deepagent/src/engine/MessageHandler.ts` — 事件分发逻辑适配
