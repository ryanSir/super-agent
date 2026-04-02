## 1. Temporal Worker 扩展

- [x] 1.1 在 `src/state/temporal_worker.py` 中新增 `run_orchestration` activity 函数，内部导入并调用 `src/gateway/rest_api.py` 的 `_run_orchestration()`
- [x] 1.2 在 `src/state/temporal_worker.py` 中新增 `OrchestratorWorkflow` 类，调用 `run_orchestration` activity，超时 600 秒，重试最多 1 次
- [x] 1.3 修改 `start_temporal_worker()` 注册 `OrchestratorWorkflow` 和 `run_orchestration` activity（保留原有 AgentWorkflow 注册）
- [x] 1.4 在 `src/state/temporal_worker.py` 中新增 `submit_orchestrator_workflow()` 函数，workflow_id = `agent-{session_id}`，提交 `OrchestratorWorkflow`

## 2. REST API 适配

- [x] 2.1 确认 `src/gateway/rest_api.py` 中 `_run_orchestration()` 函数签名为 `async def _run_orchestration(session_id, trace_id, request)` 且可被外部导入（当前已满足，无需修改）
- [x] 2.2 修改 `src/gateway/rest_api.py` 的 `submit_query()`：优先调用 `submit_orchestrator_workflow()`，失败时降级为 `asyncio.create_task(_run_orchestration())`，并推送对应事件

## 3. 应用启动集成

- [x] 3.1 修改 `src/main.py` 的 `lifespan()`：在 yield 前尝试调用 `start_temporal_worker()` 并以 `asyncio.create_task(worker.run())` 启动后台任务，连接失败时记录 WARNING 不抛异常
- [x] 3.2 修改 `src/main.py` 的 `lifespan()`：在 yield 后取消 Temporal Worker 后台任务（若存在）

## 4. 验证

- [ ] 4.1 本地启动 Temporal Server（`temporal server start-dev`），运行应用，确认日志出现 `[Temporal] Worker 启动`
- [ ] 4.2 发送 POST `/query` 请求，确认 Temporal UI（`localhost:8233`）中出现 `agent-{session_id}` workflow 记录
- [ ] 4.3 确认 SSE 事件流正常推送（`workflow_submitted` 事件 + 原有编排事件）
- [ ] 4.4 停止 Temporal Server，重新发送请求，确认系统降级为直接执行且 SSE 推送 `workflow_fallback` 事件
