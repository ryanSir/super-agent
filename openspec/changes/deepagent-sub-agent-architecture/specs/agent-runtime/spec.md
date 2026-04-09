## ADDED Requirements

### Requirement: 主 Agent 工厂

系统 SHALL 提供 agent_factory.py，使用 create_deep_agent() 创建主 Orchestrator Agent。工厂接收 ExecutionPlan 和 SubAgentConfig 列表，输出配置完整的 Agent + DeepAgentDeps。

主 Agent 的 deepagents 能力配置：
- include_todo=True（任务规划）
- include_subagents=True（Sub-Agent 委派）
- include_filesystem=False
- include_skills=False（通过桥接工具调 skill）
- include_memory=False（用自建 Redis Memory）
- context_manager=True, context_manager_max_tokens=200,000
- cost_tracking=True

#### Scenario: 创建主 Agent
- **WHEN** 收到用户请求，ReasoningEngine 输出 ExecutionPlan
- **THEN** agent_factory 创建 deepagents Agent，工具列表为 plan.resources.bridge_tools，subagents 为预置三角色配置

#### Scenario: 动态 System Prompt
- **WHEN** 创建主 Agent
- **THEN** instructions 通过 build_dynamic_instructions 动态构建，注入 Skill 摘要和用户记忆上下文

### Requirement: Hooks 体系

系统 SHALL 通过 deepagents Hooks 机制实现事件推送、循环检测和安全审计，替代自建中间件管道。

三个 Hook：
- event_push_hook：工具调用事件推送到 Redis Stream → SSE → 前端
- loop_detection_hook：滑动窗口（20次）+ MD5 去重 + 3次警告 + 5次强制停止
- audit_logger_hook：记录工具名、参数、耗时、结果到结构化日志

#### Scenario: 事件推送
- **WHEN** 主 Agent 或 Sub-Agent 调用任何工具
- **THEN** event_push_hook 将 tool_name、tool_args、result 推送到 Redis Stream，前端通过 SSE 实时接收

#### Scenario: 循环检测触发警告
- **WHEN** 同一工具（相同 name + args 的 MD5）在滑动窗口内被调用 3 次
- **THEN** loop_detection_hook 注入警告消息到对话历史

#### Scenario: 循环检测强制停止
- **WHEN** 同一工具在滑动窗口内被调用 5 次
- **THEN** loop_detection_hook 强制终止 Agent 执行

### Requirement: 两阶段流水线

系统 SHALL 采用两阶段流水线处理请求：Reason → Execute。

Stage 1（Reason）：ReasoningEngine.decide(query, mode) → ExecutionPlan
Stage 2（Execute）：agent_factory 创建 Agent → agent.run(query, deps) → OrchestratorOutput

#### Scenario: 完整请求流程
- **WHEN** 用户提交 POST /api/agent/query {query, mode}
- **THEN** Gateway 生成 session_id/trace_id → ReasoningEngine.decide() → create_orchestrator_agent() → agent.run() → Hooks 推送事件 → 返回 OrchestratorOutput

#### Scenario: DIRECT 模式快速路径
- **WHEN** ReasoningEngine 决策为 DIRECT
- **THEN** 主 Agent 直接回答或调用桥接工具，不触发 plan_and_decompose 和 Sub-Agent

### Requirement: 结构化日志

系统 SHALL 使用结构化日志，所有日志条目携带 trace_id 和 session_id。日志格式为 `[session_id][trace_id] message`。

#### Scenario: 跨层日志追踪
- **WHEN** 一个请求经过 ReasoningEngine → 主 Agent → Sub-Agent → Worker
- **THEN** 所有层级的日志条目包含相同的 trace_id，可通过 trace_id 串联完整调用链

### Requirement: 异常层级

系统 SHALL 定义业务异常基类 AgentError，所有业务异常继承自该基类。禁止裸抛 Exception。

核心异常类型：
- ReasoningError：推理引擎错误
- SubAgentError：Sub-Agent 执行错误
- WorkerError：Worker 执行错误
- BridgeError：桥接工具错误
- SandboxError / SandboxTimeoutError：沙箱相关错误

#### Scenario: Sub-Agent 超时
- **WHEN** Sub-Agent 执行超过 timeout 时间
- **THEN** 抛出 SubAgentError，主 Agent 收到 error 信息后决定重试或跳过

#### Scenario: Worker 执行失败
- **WHEN** Worker 执行抛出异常
- **THEN** BaseWorker 捕获异常，返回 WorkerResult(success=False, error=str(e))，不向上传播异常
