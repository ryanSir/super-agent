## MODIFIED Requirements

### Requirement: Orchestrator 编排入口
系统的"Python 大脑"，基于 PydanticAI 实现 Orchestrator-Workers 编排模式。负责意图理解、DAG 规划、任务路由分发、结果整合，以及 A2UI 事件推送。

`run_orchestrator()` 入口 MUST 实现三阶段管道：

1. **Classify**: 调用 `IntentRouter.classify(query, mode)` 获取 `ExecutionMode`
2. **Assemble**: 调用 `ToolSetAssembler.assemble(execution_mode)` 获取工具配置
3. **Execute**: 使用统一的 `_execute_agent()` 函数执行，传入工具配置

当 `middleware.enabled=true` 时，三阶段管道 MUST 被 `MiddlewarePipeline` 包裹。

`run_orchestrator()` MUST 接受 `mode` 参数（默认 "auto"），支持 "auto"、"direct"、"plan_and_execute" 三种值。

#### Scenario: auto 模式完整流程
- **WHEN** 用户发送 query="帮我分析这个数据"，mode="auto"
- **THEN** IntentRouter 返回 AUTO → ToolSetAssembler 返回全部工具 → Agent 自主决定是否规划

#### Scenario: direct 模式跳过规划
- **WHEN** 用户发送 query="写个快排"，mode="auto"，IntentRouter 分类为 DIRECT
- **THEN** ToolSetAssembler 过滤掉 plan_and_decompose → Agent 直接选择 execute_sandbox_task 执行

#### Scenario: plan_and_execute 模式强制规划
- **WHEN** 用户发送 query="检索专利并分析趋势"，mode="auto"，IntentRouter 分类为 PLAN_AND_EXECUTE
- **THEN** ToolSetAssembler 返回全部工具 + prompt_prefix → Agent 先调 plan_and_decompose 再执行

#### Scenario: middleware pipeline 包裹
- **WHEN** middleware.enabled=true
- **THEN** 三阶段管道在 MiddlewarePipeline 的 before_agent 和 after_agent 之间执行

#### Scenario: middleware pipeline 禁用
- **WHEN** middleware.enabled=false
- **THEN** 三阶段管道直接执行，不经过任何 middleware

## REMOVED Requirements

### Requirement: 简单任务直通规则
**Reason**: 由 IntentRouter 规则匹配替代。system prompt 中的"简单任务直通规则"段落移除，复杂度判断职责从 LLM prompt 转移到 IntentRouter 代码层。
**Migration**: IntentRouter 的规则匹配覆盖原有的 prompt 引导逻辑，无需用户侧迁移。

## ADDED Requirements

### Requirement: 统一 Agent 执行函数
系统 SHALL 提供 `_execute_agent()` 内部函数，作为所有模式的统一执行入口。该函数 MUST 处理：
- MCP toolsets 加载和 fallback
- 工具过滤（根据 AssembleResult.tool_filter）
- prompt_prefix 注入
- token usage 更新到 MiddlewareContext
- A2UI 帧注入到 OrchestratorOutput
- 会话历史保存

#### Scenario: MCP 连接失败降级
- **WHEN** MCP toolsets 加载成功但执行时连接失败
- **THEN** 自动降级为无 MCP 模式重新执行

#### Scenario: 工具过滤生效
- **WHEN** AssembleResult.tool_filter = ["plan_and_decompose"]
- **THEN** Agent 执行时 plan_and_decompose 工具不可用

#### Scenario: Agent 执行超时
- **WHEN** Agent 执行超过 asyncio 超时限制
- **THEN** 抛出 OrchestrationTimeout 异常

### Requirement: 沙箱任务重试保护
`execute_sandbox_task` 工具 MUST 对同一 task_id 限制最多 2 次执行。超过后 MUST 返回失败结果并引导 Agent 用已有信息回答用户。

#### Scenario: 沙箱重试超限
- **WHEN** 同一 task_id 的沙箱任务已执行 2 次仍失败
- **THEN** 返回 `WorkerResult(success=False, error="沙箱任务已重试 2 次仍失败，请直接用已有信息回答用户")`
