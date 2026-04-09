## MODIFIED Requirements

### Requirement: 执行模式

系统 SHALL 支持四种执行模式：DIRECT、AUTO、PLAN_AND_EXECUTE、SUB_AGENT。

- DIRECT：主 Agent 直接回答或调用单个工具，过滤规划相关工具
- AUTO：主 Agent 自主决定调用哪些工具，全量工具可用
- PLAN_AND_EXECUTE：主 Agent 先调用 plan_and_decompose 生成 DAG，再按拓扑序执行
- SUB_AGENT：主 Agent 通过 SubAgentToolset 将子任务委派给专业 Sub-Agent

#### Scenario: SUB_AGENT 模式执行
- **WHEN** ReasoningEngine 决策为 SUB_AGENT
- **THEN** 主 Agent 先调用 plan_and_decompose 生成 DAG，然后通过 task() 将各子任务委派给对应角色的 Sub-Agent

#### Scenario: 模式通过 API 指定
- **WHEN** 用户请求 mode="sub_agent"
- **THEN** 系统直接使用 SUB_AGENT 模式，跳过复杂度评估

### Requirement: OrchestratorOutput 扩展

OrchestratorOutput SHALL 新增 sub_agent_results 字段（list[dict]），记录所有 Sub-Agent 的执行结果。

#### Scenario: SUB_AGENT 模式输出
- **WHEN** 主 Agent 在 SUB_AGENT 模式下完成执行
- **THEN** OrchestratorOutput.sub_agent_results 包含每个 Sub-Agent 的 task_id、success、answer、token_usage

### Requirement: TaskType 扩展

TaskType 枚举 SHALL 新增 SUB_AGENT_TASK 值，用于 DAG 中标记需要 Sub-Agent 处理的复合任务。

#### Scenario: Planner 生成 SUB_AGENT_TASK
- **WHEN** Planner 分析到一个子任务需要多步推理（如"综合分析三个竞品"）
- **THEN** 生成 TaskNode(task_type=TaskType.SUB_AGENT_TASK)
