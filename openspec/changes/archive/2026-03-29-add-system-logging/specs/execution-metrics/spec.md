## ADDED Requirements

### Requirement: MetricsCollector 指标采集器
系统 SHALL 提供 MetricsCollector 单例，使用内存环形缓冲（deque）存储 PipelineEvent，默认容量 10000 条。

#### Scenario: 自动采集事件
- **WHEN** 一个 PipelineEvent 被记录
- **THEN** MetricsCollector MUST 自动接收并存储该事件

#### Scenario: 缓冲区满时自动淘汰
- **WHEN** 环形缓冲已满（达到 maxlen）且新事件到达
- **THEN** 系统 MUST 自动淘汰最旧的事件，不得阻塞或报错

#### Scenario: 高并发安全
- **WHEN** 多个协程同时调用 MetricsCollector.record()
- **THEN** 系统 MUST 保证线程/协程安全，不丢失事件

### Requirement: 步骤耗时统计
系统 SHALL 提供按步骤名称查询耗时统计的能力。

#### Scenario: 查询指定步骤的耗时分布
- **WHEN** 调用 `get_step_stats(step="worker.native.rag", window_minutes=5)`
- **THEN** 系统 MUST 返回 StepStats，包含：`count`（调用次数）、`avg_ms`（平均耗时）、`p50_ms`、`p95_ms`、`p99_ms`、`max_ms`、`error_count`（失败次数）、`error_rate`（失败率）

#### Scenario: 无数据时返回零值
- **WHEN** 查询的步骤在指定时间窗口内无事件
- **THEN** 系统 MUST 返回所有数值字段为 0 的 StepStats，不得抛出异常

#### Scenario: 超时统计
- **WHEN** 某步骤的 duration_ms 超过预设阈值（可配置，默认 5000ms）
- **THEN** 系统 MUST 在事件 metadata 中标记 `slow=true`

### Requirement: 链路时间线还原
系统 SHALL 支持通过 trace_id 还原完整的请求执行时间线。

#### Scenario: 查询完整链路
- **WHEN** 调用 `get_trace_timeline(trace_id="abc123")`
- **THEN** 系统 MUST 返回该 trace_id 下所有 PipelineEvent，按 timestamp 升序排列

#### Scenario: trace_id 不存在
- **WHEN** 查询的 trace_id 在缓冲区中不存在
- **THEN** 系统 MUST 返回空列表，不得抛出异常

### Requirement: 全局步骤概览
系统 SHALL 提供全局步骤概览接口，展示所有步骤的汇总统计。

#### Scenario: 获取全局概览
- **WHEN** 调用 `get_overview(window_minutes=5)`
- **THEN** 系统 MUST 返回所有在时间窗口内有事件的步骤的 StepStats 列表，按 avg_ms 降序排列

### Requirement: 指标采集不影响业务性能
指标采集 MUST 为非阻塞操作，不得对请求延迟产生可感知的影响。

#### Scenario: 采集耗时上限
- **WHEN** MetricsCollector.record() 被调用
- **THEN** 单次调用耗时 MUST 小于 1ms

#### Scenario: 采集异常不中断业务
- **WHEN** MetricsCollector 内部发生异常
- **THEN** 系统 MUST 捕获异常并记录 warning 日志，不得影响业务流程
