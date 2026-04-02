## 1. Orchestrator 流式改造

- [x] 1.1 在 `src/orchestrator/orchestrator_agent.py` 中，将最终回答生成从 `agent.run()` 改为 `agent.run_stream()`，使用 `result.stream_text(delta=True)` 迭代 token
- [x] 1.2 修改 `run_orchestrator()` 函数签名，改为 `AsyncGenerator`，在迭代过程中 yield 每个 token 字符串，流结束后 return 完整的 `OrchestratorOutput`
- [x] 1.3 在 `run_orchestrator()` 的 `try/finally` 块中确保流中断时仍发送 `session_failed` 事件，并记录已生成的部分文本长度

## 2. REST API 推送改造

- [x] 2.1 在 `src/gateway/rest_api.py` 中，删除 `asyncio.sleep(0.03)` 和固定 `chunk_size=4` 的分块循环
- [x] 2.2 改为直接消费 `run_orchestrator()` 异步生成器，每收到一个 token 立即调用 `publish_event` 推送 `text_stream` 事件
- [x] 2.3 过滤空字符串 token，不推送 `delta` 为空的 `text_stream` 事件
- [x] 2.4 在生成器耗尽后，将累积的完整文本存入 `_session_histories`

## 3. WebSocket API 推送改造

- [x] 3.1 在 `src/gateway/websocket_api.py` 中，同步执行与 REST API 相同的改造：删除 sleep 循环，改为消费生成器直接转发 token

## 4. 验证

- [ ] 4.1 本地测试：发送一条查询，验证首字延迟明显降低（目标 < 500ms）
- [ ] 4.2 测试断线重连：在流式输出过程中断开 SSE 连接，重连后验证断点续传正常
- [ ] 4.3 测试并发：同时发起两个查询，验证两个会话的 token 推送互不阻塞
- [ ] 4.4 测试异常：模拟 LLM 流中断，验证 `session_failed` 事件被正确推送（含 `partial_answer_len`）
