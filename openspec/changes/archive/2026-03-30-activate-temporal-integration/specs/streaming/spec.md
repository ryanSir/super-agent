## ADDED Requirements

### Requirement: Temporal 工作流状态事件
系统 SHALL 在工作流提交和完成时推送状态事件到 Redis Streams，使客户端可通过 SSE 感知 Temporal 执行状态。

#### Scenario: 工作流提交成功事件
- **WHEN** `submit_orchestrator_workflow()` 成功提交工作流到 Temporal
- **THEN** 系统 MUST 推送 `workflow_submitted` 事件，包含 `workflow_id` 和 `run_id` 字段

#### Scenario: Temporal 降级为直接执行
- **WHEN** Temporal 不可用，系统降级为直接 `asyncio.create_task` 执行
- **THEN** 系统 MUST 推送 `workflow_fallback` 事件，`detail` 字段说明降级原因，后续事件流与正常路径一致

#### Scenario: 前端忽略未知 Temporal 事件
- **WHEN** 前端收到 `workflow_submitted` 或 `workflow_fallback` 事件
- **THEN** 前端 MUST 忽略或仅作日志记录，不影响正常 UI 渲染流程
