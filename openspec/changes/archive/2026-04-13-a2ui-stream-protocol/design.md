## Context

当前 `_execute_plan` 使用 `agent.iter()` 遍历执行节点，但只推送了 `tool_call` 一种事件。A2UI 规范定义了完整的事件帧体系（`text_stream`、`render_widget`、`tool_result`、`process_update`），但后端没有实际生成和推送这些事件。前端 `MessageHandler.ts` 已有按 `event_type` 分发的骨架，但因为收不到事件所以无法渲染。

核心矛盾：PydanticAI 的 `agent.iter()` 产出的是 graph node（`ModelRequestNode`、`CallToolsNode`、`End`），需要一个转换层将 node 映射为 A2UI 事件帧。

## Goals / Non-Goals

**Goals:**
- 定义统一的 SSE 事件数据格式，所有事件遵循 A2UIFrame 基类
- 在 `agent.iter()` 循环中，将每种 node 类型映射为对应的 A2UI 事件
- LLM 文本输出通过 `text_stream` 事件流式推送（delta 增量）
- 工具调用结果通过 `tool_result` 事件推送，`emit_chart` 返回值额外推送 `render_widget`
- 阶段切换通过 `process_update` 事件推送

**Non-Goals:**
- 不实现 WebSocket 双向通道
- 不新增前端组件类型
- 不实现消息持久化或回放

## Decisions

### Decision 1: 事件帧统一格式

所有 SSE 事件采用统一的 JSON 信封格式：

```json
{
  "event_type": "text_stream | render_widget | tool_result | process_update",
  "trace_id": "t-xxx",
  "session_id": "sess-xxx",
  "timestamp": "2026-04-10T17:34:51.000Z",
  ...payload
}
```

**理由**: 前端只需按 `event_type` 分发，不需要解析 SSE 的 `event:` 字段。统一信封简化了前端处理逻辑和断点续传。

**备选方案**: 用 SSE 原生 `event:` 字段区分类型 → 放弃，因为 Redis Stream 存储的是 JSON，不携带 SSE 元数据。

### Decision 2: Node → Event 映射策略

| PydanticAI Node | A2UI Event | 说明 |
|----------------|------------|------|
| `ModelRequestNode` (streaming) | `text_stream` | 通过 `node.stream()` 获取 delta |
| `CallToolsNode` | `tool_result` | 从 `node.tool_call_results` 提取 |
| `CallToolsNode` (emit_chart) | `render_widget` | 检测 tool_name，额外推送 widget 帧 |
| 阶段切换 | `process_update` | planning → executing → completed |
| `End` | `text_stream(is_final=true)` | 标记流结束 |

**理由**: 一对一映射最简单，不引入中间抽象层。`emit_chart` 的特殊处理通过 tool_name 检测实现，不需要改工具签名。

### Decision 3: text_stream 流式推送方式

使用 `agent.iter()` 的 `ModelRequestNode` 节点，调用 `node.stream()` 获取 token 级别的增量文本，每个 chunk 作为一个 `text_stream` 事件推送。

**理由**: `agent.iter()` 已经支持节点级遍历，`stream()` 提供 token 粒度。不需要切换到 `agent.run_stream()`。

**备选方案**: 使用 `agent.run_stream()` 全局流 → 放弃，因为丢失了节点类型信息，无法区分工具调用和文本输出。

### Decision 4: render_widget 事件生成

`emit_chart` 工具返回值中已包含 `component` 和 `props`，在 `CallToolsNode` 处理时检测 tool_name 为 `emit_chart`，将返回值转换为 `render_widget` 事件推送。

```python
if tool_name == "emit_chart" and result.get("success"):
    await publish(session_id, {
        "event_type": "render_widget",
        "widget_id": f"chart-{uuid4().hex[:8]}",
        "ui_component": result["data"]["component"],
        "props": result["data"]["props"],
    })
```

**理由**: 不改变 `emit_chart` 的工具签名，只在流式管道层做事件转换。

## Risks / Trade-offs

- [Risk] `ModelRequestNode.stream()` 可能不被所有 model provider 支持 → 降级为等待完整响应后一次性推送 `text_stream(is_final=true)`
- [Risk] 高频 `text_stream` 事件可能导致 Redis Stream 写入压力 → 设置 batch 间隔（200ms 合并一次），或直接通过 SSE 推送不经 Redis
- [Trade-off] 事件不经 Redis 直接推送 SSE 会丢失断点续传能力 → 对 `text_stream` 可接受，因为文本流不需要回放；`render_widget` 仍走 Redis

## Open Questions

1. `text_stream` 事件是否需要经过 Redis Stream？如果直接推 SSE 可以降低延迟但丢失断点续传
2. 是否需要为 `render_widget` 事件支持 `update_widget`（更新已渲染的图表数据）？当前只做首次渲染
