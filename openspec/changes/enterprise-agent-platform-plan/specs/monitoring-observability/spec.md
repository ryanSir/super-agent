## ADDED Requirements

### Requirement: Langfuse LLM 交互监控
系统 SHALL 集成 Langfuse，追踪每次 LLM 交互的 token 消耗、延迟、成本、prompt 版本。每个请求 SHALL 生成完整的 trace，包含所有 LLM 调用和工具调用的 span。

#### Scenario: Trace 生成
- **WHEN** 一次用户请求触发 3 次 LLM 调用和 2 次工具调用
- **THEN** Langfuse SHALL 记录 1 个 trace + 5 个 span，包含父子关系

#### Scenario: 成本追踪
- **WHEN** 请求使用 gpt-4o 消耗 1000 input tokens + 500 output tokens
- **THEN** Langfuse SHALL 记录 token 数量和估算成本

#### Scenario: Langfuse 不可用降级
- **WHEN** Langfuse 服务不可用
- **THEN** 系统 SHALL 降级为本地结构化日志，不影响主流程

### Requirement: ARMS 应用监控
系统 SHALL 集成 ARMS（应用实时监控服务），实现链路追踪和异常告警。每个请求 SHALL 携带 trace_id 贯穿全链路。

#### Scenario: 链路追踪
- **WHEN** 请求经过 Gateway → ReasoningEngine → Agent → Worker
- **THEN** ARMS SHALL 记录完整调用链，每个环节的耗时和状态

#### Scenario: 异常告警
- **WHEN** 错误率超过阈值（默认 5%）或 P99 延迟超过 30 秒
- **THEN** ARMS SHALL 触发告警通知（钉钉/邮件）

### Requirement: Prometheus 指标导出
系统 SHALL 导出 Prometheus 格式的指标，包括：请求 QPS、延迟分布（P50/P95/P99）、错误率、活跃会话数、沙箱使用率、LLM token 消耗速率。

#### Scenario: 指标端点
- **WHEN** Prometheus 抓取 /metrics 端点
- **THEN** 系统 SHALL 返回所有指标的当前值，格式符合 Prometheus exposition format

#### Scenario: Grafana 看板
- **WHEN** 运维人员访问 Grafana
- **THEN** SHALL 看到预配置的看板：请求概览、LLM 性能、沙箱状态、错误分析

### Requirement: Pipeline 事件计时
系统 SHALL 记录每个处理阶段的耗时和元数据，支持性能分析和瓶颈定位。

#### Scenario: 阶段计时
- **WHEN** 请求经过 13-stage Middleware Pipeline
- **THEN** 每个 stage 的 start_time、end_time、duration SHALL 被记录并可查询

#### Scenario: 慢请求分析
- **WHEN** 请求总耗时超过 30 秒
- **THEN** 系统 SHALL 标记为慢请求，记录各阶段耗时明细

### Requirement: 结构化日志
系统 SHALL 使用结构化日志格式（JSON），每条日志 SHALL 包含 trace_id、session_id、request_id、timestamp、level、module、message。

#### Scenario: 日志关联
- **WHEN** 排查某个请求的问题
- **THEN** 通过 trace_id SHALL 能查到该请求全链路的所有日志

#### Scenario: 日志级别控制
- **WHEN** 配置 LOG_LEVEL=WARNING
- **THEN** 系统 SHALL 只输出 WARNING 及以上级别的日志
