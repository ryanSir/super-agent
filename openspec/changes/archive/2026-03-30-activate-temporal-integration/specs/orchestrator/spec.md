## MODIFIED Requirements

### Requirement: 编排入口
`run_orchestrator()` 入口 MUST 实现三阶段管道：

1. **Classify**: 调用 `IntentRouter.classify(query, mode)` 获取 `ExecutionMode`
2. **Assemble**: 调用 `ToolSetAssembler.assemble(execution_mode)` 获取工具配置
3. **Execute**: 使用统一的 `_execute_agent()` 函数执行，传入工具配置

当 `middleware.enabled=true` 时，三阶段管道 MUST 被 `MiddlewarePipeline` 包裹。

`run_orchestrator()` MUST 接受 `mode` 参数（默认 "auto"），支持 "auto"、"direct"、"plan_and_execute" 三种值。

`_run_orchestration()` 函数 MUST 作为独立的可复用函数导出，供 Temporal Activity 直接调用。该函数签名 MUST 为：
```python
async def _run_orchestration(session_id: str, trace_id: str, request: QueryRequest) -> None
```

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

#### Scenario: _run_orchestration 被 Temporal Activity 调用
- **WHEN** Temporal `run_orchestration` activity 调用 `_run_orchestration(session_id, trace_id, request)`
- **THEN** 函数 MUST 正常执行完整编排流程，通过 `publish_event()` 推送所有事件到 Redis Streams
