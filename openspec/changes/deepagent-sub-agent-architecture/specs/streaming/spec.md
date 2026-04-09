## MODIFIED Requirements

### Requirement: Sub-Agent 生命周期事件

SSE 事件流 SHALL 新增 Sub-Agent 生命周期事件类型：

- sub_agent_started：Sub-Agent 开始执行，包含 sub_agent_name、task_id
- sub_agent_progress：Sub-Agent 中间进度（可选），包含 sub_agent_name、task_id、progress
- sub_agent_completed：Sub-Agent 执行完成，包含 sub_agent_name、task_id、success、token_usage

事件通过 event_push_hook 推送到 Redis Stream，前端通过 SSE 实时接收。

#### Scenario: Sub-Agent 事件推送
- **WHEN** 主 Agent 委派 researcher Sub-Agent 执行任务
- **THEN** SSE 流依次推送 sub_agent_started → （可选 sub_agent_progress）→ sub_agent_completed 事件

#### Scenario: 并行 Sub-Agent 事件交错
- **WHEN** 三个 Sub-Agent 并行执行
- **THEN** SSE 流中三个 Sub-Agent 的事件按实际完成顺序交错推送，每个事件通过 task_id 区分归属

#### Scenario: Sub-Agent 失败事件
- **WHEN** Sub-Agent 执行失败或超时
- **THEN** 推送 sub_agent_completed 事件，success=false，error 字段包含失败原因
