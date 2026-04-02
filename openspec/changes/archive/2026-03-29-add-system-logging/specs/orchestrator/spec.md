## MODIFIED Requirements

### Requirement: Orchestrator 编排流程日志
Orchestrator 的 `run_orchestrator()` 函数 SHALL 在以下关键步骤使用 `pipeline_step` 记录标准化事件：
1. 意图分类（`intent.classify`）
2. 工具集装配（`toolset.assemble`）
3. 任务规划（`orchestrator.plan`）
4. Agent 执行（`orchestrator.execute`）

#### Scenario: 编排全流程事件记录
- **WHEN** `run_orchestrator()` 被调用并成功完成
- **THEN** 系统 MUST 记录至少 4 对 started/completed 事件，覆盖 intent.classify、toolset.assemble、orchestrator.plan、orchestrator.execute

#### Scenario: 规划阶段失败
- **WHEN** `plan_and_decompose()` 执行过程中抛出异常
- **THEN** 系统 MUST 记录 `orchestrator.plan` 的 failed 事件，metadata 包含错误信息，且不影响错误的正常传播

#### Scenario: 规划结果记录
- **WHEN** `plan_and_decompose()` 成功完成
- **THEN** completed 事件的 metadata MUST 包含 `task_count`（规划的任务数量）

### Requirement: Orchestrator Tool 调用日志
Orchestrator 的每个 tool 函数（execute_native_worker, execute_sandbox_task, execute_skill）SHALL 使用 `pipeline_step` 记录执行事件。

#### Scenario: Native Worker 调用事件
- **WHEN** `execute_native_worker()` 被调用
- **THEN** 系统 MUST 记录 `worker.native.{type}` 事件，metadata 包含 `worker_type` 和 `task_id`

#### Scenario: Sandbox 任务事件
- **WHEN** `execute_sandbox_task()` 被调用
- **THEN** 系统 MUST 记录 `worker.sandbox` 事件，metadata 包含 `task_id`

#### Scenario: Skill 执行事件
- **WHEN** `execute_skill()` 被调用
- **THEN** 系统 MUST 记录 `skill.execute.{name}` 事件，metadata 包含 `skill_name`
