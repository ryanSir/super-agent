## 1. 后端：改造 _execute_agent 使用 run_stream()

- [x] 1.1 在 `src/orchestrator/orchestrator_agent.py` 的 `_execute_agent` 中，将 `agent.run()` 替换为 `agent.run_stream()`，完整消费 `stream_events()` 迭代器
- [x] 1.2 在 `stream_events()` 循环中拦截 `ToolCallPart`，推送 `tool_call` SSE 事件（含 `tool_name`、`tool_type: "mcp"`）
- [x] 1.3 在 `stream_events()` 循环中拦截 `ToolReturnPart`，推送 `tool_result` SSE 事件（含 `tool_name`、`content`、`status: "success"`），对 content 做 `str()` 兜底转换
- [x] 1.4 将 MCP fallback 的 `agent.run()` 也改为 `agent.run_stream()`，保持降级逻辑不变
- [x] 1.5 从 `result.output` 取最终输出，保持 token usage 统计和 `_session_histories` 消息历史保存逻辑不变

## 2. 前端：MessageHandler 支持 tool_call 事件

- [x] 2.1 在 `frontend/src/engine/MessageHandler.ts` 的 `UIState` 中，为 `ToolResultState` 新增可选字段 `loading?: boolean`
- [x] 2.2 在 `handleEvent` 的 `switch` 中新增 `tool_call` case，向 `toolResults` 追加一条 `loading: true` 的占位记录
- [x] 2.3 在 `tool_result` case 中，匹配已有 loading 占位（按 `tool_name`），将其替换为真实结果；若无占位则直接追加

## 3. 前端：ToolResultCard 展示 loading 状态

- [x] 3.1 在 `frontend/src/components/ToolResultCard.tsx` 中，当 `loading: true` 时渲染 loading 骨架（工具名 + 动画点）
- [x] 3.2 在 `NAME_ICONS` 中补充 `patsnap_search: '🔍'`（当前缺失）
