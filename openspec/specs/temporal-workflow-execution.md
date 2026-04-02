# Temporal Workflow Execution 规格

## 职责

将 Orchestrator 编排逻辑托管到 Temporal，实现持久化、可重试的工作流执行。
提供 Worker 生命周期管理、Workflow 定义、Activity 封装，以及工作流提交接口。

## 核心文件

- `src/temporal/worker.py` — Temporal Worker 初始化与生命周期管理
- `src/temporal/workflows.py` — OrchestratorWorkflow 定义
- `src/temporal/activities.py` — run_orchestration Activity 实现
- `src/temporal/client.py` — Temporal 客户端与工作流提交接口

## Requirements

### Requirement: Temporal Worker 生命周期管理
系统 SHALL 在 FastAPI 应用启动时自动初始化并启动 Temporal Worker，在应用关闭时优雅停止。Worker MUST 注册 `OrchestratorWorkflow` 和 `run_orchestration` activity。

#### Scenario: 应用启动时 Worker 自动启动
- **WHEN** FastAPI 应用通过 lifespan 启动
- **THEN** 系统 MUST 尝试连接 Temporal Server 并启动 Worker 后台任务，记录启动日志

#### Scenario: Temporal Server 不可用时降级
- **WHEN** FastAPI 启动时 Temporal Server 连接失败
- **THEN** 系统 MUST 记录 WARNING 日志，应用继续正常启动，不抛出异常

#### Scenario: 应用关闭时 Worker 优雅停止
- **WHEN** FastAPI 应用收到关闭信号
- **THEN** Temporal Worker 后台任务 MUST 被取消，不阻塞关闭流程

### Requirement: OrchestratorWorkflow 定义
系统 SHALL 提供 `OrchestratorWorkflow`，作为薄包装层调用 `run_orchestration` activity，将完整编排逻辑委托给现有 PydanticAI orchestrator。

#### Scenario: 工作流正常执行
- **WHEN** `OrchestratorWorkflow.run()` 被调用，参数包含 `query`、`session_id`、`trace_id`、`context`、`mode`
- **THEN** 工作流 MUST 调用 `run_orchestration` activity 并等待完成，超时 600 秒

#### Scenario: 同一 session_id 重复提交
- **WHEN** 相同 `session_id` 的工作流已在运行中，再次提交
- **THEN** Temporal MUST 返回已有工作流 handle，不重复执行（workflow_id = `agent-{session_id}`）

### Requirement: run_orchestration Activity
系统 SHALL 提供 `run_orchestration` activity，内部调用现有 `_run_orchestration()` 函数执行完整编排流程，包括事件推送到 Redis Streams。

#### Scenario: Activity 正常执行
- **WHEN** `run_orchestration` activity 被调用
- **THEN** MUST 调用 `_run_orchestration(session_id, trace_id, request)` 并将所有 `publish_event()` 事件推送到 Redis Streams

#### Scenario: Activity 执行失败
- **WHEN** `_run_orchestration()` 抛出未捕获异常
- **THEN** activity MUST 将异常传播给 Temporal，由 Temporal 决定是否重试（最多 1 次）

### Requirement: 工作流提交接口
系统 SHALL 提供 `submit_orchestrator_workflow()` 函数，供 REST API 调用，提交 `OrchestratorWorkflow` 到 Temporal。

#### Scenario: 提交成功
- **WHEN** `submit_orchestrator_workflow(query, session_id, trace_id, context, mode)` 被调用且 Temporal 可用
- **THEN** MUST 返回 workflow run_id，记录提交日志

#### Scenario: Temporal 不可用时抛出异常
- **WHEN** Temporal 客户端未初始化或连接断开
- **THEN** MUST 抛出异常，由调用方决定降级策略
