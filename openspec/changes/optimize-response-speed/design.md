## Context

当前系统的文本输出流程存在两层人为延迟：

1. **假流式问题**：`run_orchestrator()` 等待 LLM 完整推理结束后返回完整字符串，再由 `rest_api.py` 模拟分块推送。用户的首字等待时间 = LLM 完整推理时间（通常 3-10 秒）。

2. **人为 sleep 延迟**：`rest_api.py` 和 `websocket_api.py` 中以 `chunk_size=4` + `asyncio.sleep(0.03)` 模拟打字机效果，1000字回答额外增加约 7.5 秒等待。

当前数据流：
```
LLM 推理（完整等待）→ 返回完整字符串 → 分块循环 + sleep(0.03) → publish_event → Redis → SSE → 前端
```

目标数据流：
```
LLM 推理（token 流）→ 每个 token 立即 publish_event → Redis → SSE → 前端
```

## Goals / Non-Goals

**Goals:**
- 消除 `asyncio.sleep(0.03)` 人为延迟
- 将 LLM 调用改为真正的 token 级流式（PydanticAI `run_stream()`）
- 首字延迟从"完整推理时间"降低到"首 token 时间"（通常 < 500ms）

**Non-Goals:**
- 不修改 Worker 执行逻辑
- 不更换 LLM 模型
- 不修改 SSE 协议结构或前端代码

## Decisions

### 决策 1：使用 PydanticAI `run_stream()` 替代 `run()`

**选择**：将 `orchestrator_agent.run()` 改为 `orchestrator_agent.run_stream()`，在 `async with` 块内通过 `result.stream_text()` 迭代 token。

**理由**：PydanticAI 原生支持流式输出，`stream_text(delta=True)` 直接返回增量 token，无需额外处理。

**替代方案**：使用 LiteLLM 直接调用 streaming API——但这会绕过 PydanticAI 的工具调用和类型验证层，改动范围更大。

### 决策 2：Orchestrator 返回异步生成器

**选择**：`run_orchestrator()` 函数签名从返回 `OrchestratorOutput` 改为 `AsyncGenerator[str, OrchestratorOutput]`，在 yield token 的同时，最终 return 完整的 output 对象。

**理由**：调用方（`rest_api.py`）需要同时获得流式 token（用于实时推送）和最终结构化输出（用于会话历史存储）。Python 异步生成器支持通过 `StopAsyncIteration.value` 返回最终值。

**替代方案**：用回调函数传递 token——但生成器模式更 Pythonic，与现有 async/await 风格一致。

### 决策 3：移除打字机 sleep，保留自然 token 边界

**选择**：直接删除 `asyncio.sleep(0.03)` 和固定 `chunk_size=4` 的分块循环，改为直接转发 LLM 原生 token。

**理由**：LLM 本身的输出速度（约 30-60 token/秒）已经产生自然的打字机视觉效果，人为 sleep 只会增加延迟而不改善体验。

## Risks / Trade-offs

- **[风险] 流式中断处理**：若 LLM 流在中途断开，需确保 `session_failed` 事件仍被发送，避免前端永久等待。→ 缓解：在 `run_orchestrator()` 的 `try/finally` 块中保证发送终止事件。

- **[风险] 会话历史完整性**：流式模式下，完整回答需要等所有 token 收集完毕才能存入 `_session_histories`。→ 缓解：在生成器耗尽后，将累积的完整文本存入历史。

- **[Trade-off] 断点续传行为变化**：原来的假流式模式下，断线重连可以重放所有已推送的 token（因为都已存入 Redis Stream）。真流式模式下行为不变——每个 token 推送时即写入 Redis，断点续传仍然有效。

## Migration Plan

1. 修改 `src/orchestrator/orchestrator_agent.py`：将最终 answer 生成改为 `run_stream()`
2. 修改 `src/gateway/rest_api.py`：移除 sleep 循环，改为消费生成器
3. 修改 `src/gateway/websocket_api.py`：同上
4. 本地测试：验证首字延迟、断点续传、会话历史完整性
5. 无需数据库迁移，无需前端改动

**回滚**：git revert 即可，无状态变更。

## Open Questions

- PydanticAI `run_stream()` 在工具调用（tool use）期间是否也支持流式？还是只有最终文本输出支持流式？需确认 Orchestrator 的工具调用阶段是否受影响。
