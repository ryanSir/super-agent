## Context

当前 `/query` 端点通过 `asyncio.create_task(_run_orchestration())` 在 FastAPI 进程内直接执行编排逻辑。Temporal 的 Worker、Workflow、Activity 已全部定义完毕（`src/state/`），但未接入请求流程。

现有 `AgentWorkflow` 是 DAG plan-and-execute 模型，与当前 PydanticAI Agent（单 Agent + 工具调用）是两套不同的执行架构。直接切换到 DAG 模型风险高、改动大。

**激活策略：薄包装（Thin Wrapper）**

不替换现有 PydanticAI 编排逻辑，而是将 `_run_orchestration()` 整体包装为一个 Temporal Activity，通过一个简单的 `OrchestratorWorkflow` 调用。这样：
- 保留所有现有编排逻辑不变
- 获得 Temporal 的持久化、崩溃恢复、任务去重
- 最小化改动范围

现有 `AgentWorkflow`（DAG 模型）保留，作为未来演进路径。

## Goals / Non-Goals

**Goals:**
- FastAPI 启动时自动启动 Temporal Worker
- `/query` 端点提交 `OrchestratorWorkflow` 替代直接 `create_task`
- Activity 内部通过 `publish_event()` 推送事件到 Redis Streams，SSE 通道不变
- 同一 `session_id` 的重复提交自动去重（Temporal workflow_id 唯一性保证）

**Non-Goals:**
- 不激活现有 `AgentWorkflow`（DAG 模型），保留为未来演进
- 不修改 SSE/WebSocket 端点
- 不引入 Temporal UI 或外部监控
- 不修改 E2B 沙箱执行逻辑

## Decisions

### 决策 1：新建 OrchestratorWorkflow，不复用 AgentWorkflow

**选择**：新建 `OrchestratorWorkflow`，包含单个 `run_orchestration` activity。

**原因**：现有 `AgentWorkflow` 是 DAG 模型，需要 `plan_task`/`execute_native_worker`/`collect_results` 等多个 activity 协作，与当前 PydanticAI 单 Agent 模型不兼容。强行复用会导致两套逻辑混用，增加调试难度。

**备选方案**：直接修改 `AgentWorkflow` 调用 `run_orchestrator()` — 会破坏 AgentWorkflow 的语义，不选。

### 决策 2：Worker 在 FastAPI lifespan 中以后台任务启动

**选择**：在 `main.py` 的 `lifespan` 中 `asyncio.create_task(worker.run())` 启动 Temporal Worker。

**原因**：Temporal Worker 的 `run()` 是长期运行的协程，适合作为 asyncio 后台任务与 FastAPI 共存于同一进程。无需独立进程，降低部署复杂度。

**备选方案**：独立 worker 进程 — 需要进程管理（supervisord/k8s sidecar），POC 阶段过重，不选。

### 决策 3：Activity 超时设置为 600 秒

**原因**：`run_orchestrator()` 包含 LLM 调用链，复杂任务可能超过 300 秒。设置 600 秒留足余量，重试策略设为最多 1 次（编排失败重试意义不大，且会重复推送事件）。

### 决策 4：Temporal 连接失败时降级为直接执行

**选择**：若 Temporal 客户端连接失败，`/query` 端点降级为原有 `asyncio.create_task(_run_orchestration())` 路径，并记录警告日志。

**原因**：POC 阶段 Temporal Server 可能未启动，降级保证系统可用性。

## Risks / Trade-offs

- [Activity 内 asyncio 事件循环] Temporal Activity 在 worker 线程池中运行，`run_orchestrator()` 使用 `async for`，需确认 activity 以 async 方式注册 → 已确认 `@activity.defn` 支持 async 函数，无问题
- [事件重复推送] 若 activity 重试，`publish_event()` 会重复推送 `session_created` 等事件 → 前端需幂等处理，或 activity 重试前清理 Redis Stream（暂不处理，POC 阶段可接受）
- [session_id 唯一性] Temporal workflow_id = `agent-{session_id}`，同一 session 重复提交会返回已有 workflow handle，不会重复执行 → 符合预期

## Migration Plan

1. 在 `src/state/temporal_worker.py` 新增 `OrchestratorWorkflow` 和 `run_orchestration` activity
2. 修改 `src/main.py` lifespan 启动 Temporal Worker（带降级）
3. 修改 `src/gateway/rest_api.py` 的 `submit_query()`，优先调用 `submit_workflow()`，失败时降级
4. 本地启动 Temporal Server（`temporal server start-dev`）验证端到端流程

**回滚**：删除 lifespan 中的 worker 启动代码，`submit_query()` 恢复 `create_task` 路径即可。

## Open Questions

- `src/main.py` 的 lifespan 是否已存在？需确认入口文件结构。
