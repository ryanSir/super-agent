## Why

当前系统的编排逻辑直接在 FastAPI 请求进程内同步执行，进程重启或长任务超时会导致执行状态丢失，无法恢复。Temporal 的基础设施已经定义完毕但未激活，现在将其接入主请求流程，获得持久化执行、崩溃恢复和任务去重能力。

## What Changes

- 在应用启动时初始化并启动 Temporal Worker（注册 `AgentWorkflow` 和四个 Activity）
- 修改 REST API `/query` 端点，将请求提交到 Temporal 工作流（`submit_workflow()`），替代直接调用 `run_orchestrator()`
- 实现工作流执行结果的 SSE 流式回传（通过 Redis Streams 桥接 Temporal Activity 输出与客户端）
- Activity 内部复用现有 `run_orchestrator()` 逻辑，避免重复实现

## Capabilities

### New Capabilities

- `temporal-workflow-execution`: Temporal Worker 生命周期管理、工作流提交、Activity 注册与执行

### Modified Capabilities

- `orchestrator`: 编排入口从直接函数调用改为 Temporal Activity 包装调用
- `streaming`: SSE 事件源从进程内直接 publish 改为经由 Temporal Activity → Redis Streams → SSE 的异步路径

## Impact

- `src/state/temporal_worker.py` — 补全 worker 启动逻辑，集成到 FastAPI lifespan
- `src/state/activities.py` — `execute_native_worker` / `execute_sandbox_worker` 复用现有 worker 实现
- `src/gateway/rest_api.py` — `/query` 端点改为调用 `submit_workflow()`，增加工作流状态轮询
- `src/state/workflows.py` — 确认 DAG 执行逻辑与现有 orchestrator 工具对齐
- 新增依赖：`temporalio`（已在 pyproject.toml 中，确认版本）

## Non-goals

- 不迁移 WebSocket 通道，仅处理 SSE 主通道
- 不修改 Temporal 工作流的 DAG 分解逻辑，复用现有 `plan_task` activity
- 不引入 Temporal UI 或外部监控集成
- 不修改 E2B 沙箱执行逻辑本身