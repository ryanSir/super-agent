## Why

MCP 工具（`patsnap_search`、`patsnap_fetch`）通过 pydantic-ai 的 `agent.run()` 执行，结果被吞进黑盒，前端无法感知工具调用过程和结果。用户看不到专利搜索、论文检索的中间结果，体验割裂。

## What Changes

- **后端**：`_execute_agent` 从 `agent.run()` 改为 `agent.run_stream()`，拦截 pydantic-ai 的 `ToolReturnPart` 事件，实时推送 `tool_result` SSE 事件
- **后端**：同步推送 `tool_call` 事件（工具开始调用时），让前端展示 loading 状态
- **前端**：`ToolResultCard` 补充 `patsnap_search` / `patsnap_fetch` 图标，支持专利结果的结构化展示

## Capabilities

### New Capabilities

- `mcp-tool-result-streaming`: 从 pydantic-ai streaming API 捕获 MCP 工具调用和结果，实时推送为 SSE 事件

### Modified Capabilities

- `streaming`: 新增 `tool_call` 事件类型（工具开始调用时推送，用于前端 loading 状态）
- `orchestrator`: `_execute_agent` 改用 `agent.run_stream()`，保持 token usage、消息历史等现有逻辑不变

## Non-goals

- 不修改 Skill 和 Native Worker 的 `tool_result` 推送逻辑（已正常工作）
- 不对专利/论文结果做结构化解析，`content` 仍为字符串，由前端 Markdown 渲染
- 不修改前端 `ToolResultCard` 的折叠交互逻辑

## Impact

- `src/orchestrator/orchestrator_agent.py`：`_execute_agent` 函数改造
- `src/streaming/streaming.md`：新增 `tool_call` 事件规格
- `frontend/src/components/ToolResultCard.tsx`：补充 MCP 工具图标
