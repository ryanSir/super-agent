## Why

当前响应输出存在两个主要性能问题：一是代码中人为引入了 30ms/4字符 的分块延迟，导致1000字回答需要额外等待约7.5秒；二是 LLM 响应采用"假流式"——等待模型完整输出后再模拟分块推送，用户需等待整个推理完成才能看到第一个字。

## What Changes

- 移除 `rest_api.py` 和 `websocket_api.py` 中的人为 `asyncio.sleep(0.03)` 延迟
- 将 LLM 调用从"等待完整响应再分块"改为真正的 token 级流式输出（PydanticAI streaming API）
- 优化 `chunk_size`，改为按自然语言边界（句子/词）分块，而非固定字符数
- 前端 `text_stream` 事件处理保持不变，无需修改

## Non-goals

- 不优化 LLM 模型本身的推理速度（模型选型不在本次范围内）
- 不修改 Worker 执行逻辑（RAG、DB、Sandbox 的延迟不在本次范围）
- 不引入新的缓存层或 CDN
- 不修改 SSE 协议结构或断点续传机制

## Capabilities

### New Capabilities

- `llm-true-streaming`: Orchestrator 直接将 LLM token 流实时转发到 Redis Stream，实现真正的流式输出，首字延迟从"完整推理时间"降低到"首 token 时间"

### Modified Capabilities

- `streaming`: 更新流式推送规范，`text_stream` 事件的 `delta` 字段从固定字符块改为 LLM 原生 token 块，移除人为延迟约束

## Impact

- `src/gateway/rest_api.py` — 移除分块循环和 sleep，改为直接转发流式 token
- `src/gateway/websocket_api.py` — 同上
- `src/orchestrator/orchestrator_agent.py` — Orchestrator 返回值从完整字符串改为异步生成器（streaming）
- `openspec/specs/streaming.md` — 更新 `text_stream` 事件规范