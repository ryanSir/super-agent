## MODIFIED Requirements

### Requirement: 消息帧定义

A2UIFrame 基类 SHALL 包含以下公共字段，所有事件帧继承此基类：

```python
class A2UIFrame(BaseModel):
    event_type: str           # 事件类型
    trace_id: str = ""        # 追踪 ID
    session_id: str = ""      # 会话 ID
    timestamp: datetime       # 事件时间戳（ISO 8601）
```

#### Scenario: 所有事件帧包含公共字段
- **WHEN** 系统生成任意 A2UI 事件帧
- **THEN** 事件 MUST 包含 `event_type`、`trace_id`、`session_id`、`timestamp` 四个字段

### Requirement: RenderWidget 帧生成

Orchestrator 通过 `emit_chart` 工具生成 `RenderWidget` 帧时，系统 SHALL 自动填充 `widget_id`、`session_id`、`trace_id`、`timestamp` 字段。

#### Scenario: emit_chart 生成完整 RenderWidget 帧
- **WHEN** Agent 调用 `emit_chart` 工具
- **THEN** 系统 MUST 生成 `RenderWidget` 帧，`widget_id` 格式为 `chart-{uuid8}`，`ui_component="DataChart"`，`props` 包含 `title`、`chartType`、`xAxis`、`seriesData`

#### Scenario: widget_id 全局唯一
- **WHEN** 同一会话中多次调用 `emit_chart`
- **THEN** 每次生成的 `widget_id` MUST 不同

### Requirement: TextStream 帧格式

`TextStream` 帧 SHALL 支持增量文本推送，前端按 `delta` 字段拼接显示。

#### Scenario: 增量文本推送
- **WHEN** LLM 输出一个 token
- **THEN** 系统 SHOULD 推送 `TextStream` 帧，`delta` 为该 token 文本，`is_final=false`

#### Scenario: 文本流结束标记
- **WHEN** LLM 输出完成
- **THEN** 系统 MUST 推送 `TextStream` 帧，`delta=""`，`is_final=true`

#### Scenario: 前端拼接增量文本
- **WHEN** 前端收到多个 `text_stream` 事件
- **THEN** 前端 MUST 按顺序拼接 `delta` 字段，直到收到 `is_final=true`
