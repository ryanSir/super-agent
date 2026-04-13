## 1. 数据模型

- [x] 1.1 创建 `src_deepagent/schemas/a2ui.py`，定义 `A2UIFrame` 基类和 `TextStreamFrame`、`RenderWidgetFrame`、`ToolResultFrame`、`ProcessUpdateFrame` 子类
- [x] 1.2 在 `A2UIFrame` 基类中实现 `to_event_dict()` 方法，输出包含 `event_type`、`trace_id`、`session_id`、`timestamp` 的标准 JSON dict

## 2. 流式管道核心

- [x] 2.1 重构 `rest_api.py:_execute_plan()`，在 `agent.iter()` 循环中按 node 类型生成对应 A2UI 事件帧
- [x] 2.2 `ModelRequestNode` 处理：从 `node.model_response.parts` 提取文本内容，推送 `text_stream` 事件（delta 增量）
- [x] 2.3 `CallToolsNode` 处理：从 `node.tool_call_results` 提取工具执行结果，推送 `tool_result` 事件
- [x] 2.4 `CallToolsNode` 特殊处理：检测 `tool_name == "emit_chart"`，额外推送 `render_widget` 事件，`widget_id` 格式为 `chart-{uuid8}`
- [x] 2.5 `End` 节点处理：推送 `text_stream(is_final=true)` 标记流结束
- [x] 2.6 阶段切换处理：在 `_run_orchestration` 中 planning → executing → completed 切换时推送 `process_update` 事件

## 3. 超限降级

- [x] 3.1 `_execute_plan` 中捕获 `UsageLimitExceeded`，从消息历史提取最后文本，推送 `text_stream(is_final=true)` + `session_completed`
- [x] 3.2 消息历史为空时推送 `session_failed` 事件

## 4. 事件发布适配

- [x] 4.1 在 `stream_adapter.py:publish()` 中自动注入 `timestamp` 和 `session_id` 字段（如果事件中缺失）
- [x] 4.2 `_run_orchestration` 中 `session_completed` 事件确保 `answer` 字段非空（从 result.output 提取）

## 5. emit_chart 工具适配

- [x] 5.1 修改 `base_tools.py:emit_chart()`，返回值中包含 `widget_id`、`ui_component`、`props` 完整字段，供流式管道直接转换为 `render_widget` 事件

## 6. 前端适配

- [x] 6.1 `MessageHandler.ts` 中补充 `text_stream` 事件处理：按 `delta` 拼接文本，`is_final=true` 时标记完成
- [x] 6.2 `MessageHandler.ts` 中补充 `tool_result` 事件处理：渲染工具调用结果卡片
- [x] 6.3 `MessageHandler.ts` 中确认 `render_widget` 事件正确分发到 `ComponentRegistry`
- [x] 6.4 验证未知 `event_type` 被静默忽略，不抛出错误
