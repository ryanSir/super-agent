## Context

当前 `_execute_agent` 使用 `agent.run()` 执行 pydantic-ai Agent，整个 agentic loop（LLM 调用 → MCP 工具执行 → 结果回传）在黑盒内完成，外部无法感知中间过程。

Native Worker 和 Skill 工具通过 `@orchestrator_agent.tool` 装饰器注册，在工具函数内部手动调用 `_push_event` 推送 `tool_result` 事件，已正常工作。

MCP 工具（`patsnap_search`、`patsnap_fetch`）由 pydantic-ai 的 MCP 客户端自动代理，不经过 `@orchestrator_agent.tool`，因此没有推送事件的机会。

## Goals / Non-Goals

**Goals:**
- MCP 工具调用开始时推送 `tool_call` 事件（前端展示 loading）
- MCP 工具执行完成后推送 `tool_result` 事件（前端展示结果卡片）
- 保持现有 token usage 统计、消息历史保存、MCP fallback 逻辑不变

**Non-Goals:**
- 不修改 Native Worker / Skill 的事件推送逻辑
- 不对工具结果做结构化解析（content 保持字符串，Markdown 渲染）
- 不支持工具执行进度（只有开始和完成两个状态）

## Decisions

### 决策 1：使用 `agent.run_stream()` 替代 `agent.run()`

pydantic-ai 的 `run_stream()` 返回一个异步上下文管理器，通过 `stream_events()` 可以逐个消费流式事件，其中包含：
- `ToolCallPart`：工具开始调用（含工具名、参数）
- `ToolReturnPart`：工具执行完成（含工具名、返回内容）

替代方案：monkey-patch MCP server 的 `call_tool` 方法注入回调。
选择 `run_stream()` 的原因：这是 pydantic-ai 官方支持的 API，不依赖内部实现细节，升级稳定性更好。

### 决策 2：`stream_events()` 消费完整流后再取 output

`run_stream()` 的 `result.output` 在流消费完毕后才可用。实现上需要完整遍历 `stream_events()` 迭代器，在遍历过程中拦截 `ToolCallPart` / `ToolReturnPart` 推送事件，最后取 `result.output`。

### 决策 3：`tool_call` 事件只推送工具名，不推送参数

MCP 工具参数可能包含大量文本（如查询语句），推送完整参数会增加 SSE 流量且前端暂无展示需求。只推送 `tool_name` 用于前端展示 loading 状态。

### 决策 4：MCP fallback 保持不变

现有 fallback 逻辑（MCP 连接失败时降级为无 MCP 模式）在 `run_stream()` 下同样适用，`except` 块内改用 `run_stream()` 即可。

## Risks / Trade-offs

- **[风险] pydantic-ai 版本升级可能改变 stream event 类型名** → 在事件拦截处加 `isinstance` 检查，不依赖字符串匹配
- **[风险] `run_stream()` 的 `result.output` 在流未完全消费时不可用** → 必须完整消费 `stream_events()` 迭代器，不能提前 break
- **[Trade-off] `tool_call` 事件在工具开始时推送，但 MCP 工具执行可能很快** → 前端 loading 状态可能一闪而过，可接受

## Migration Plan

1. 修改 `_execute_agent`：`agent.run()` → `agent.run_stream()`，加入事件拦截逻辑
2. 在 `streaming.md` spec 中补充 `tool_call` 事件定义
3. 前端 `ToolResultCard` 补充 `patsnap_search` / `patsnap_fetch` 图标（已有 `NAME_ICONS` 映射）
4. 无需数据迁移，无需停机

回滚：将 `agent.run_stream()` 改回 `agent.run()` 即可，无状态变更。

## Open Questions

- `ToolReturnPart.content` 的类型：pydantic-ai 返回的是字符串还是结构化对象？需在实现时确认并做 `str()` 兜底转换。
