## MODIFIED Requirements

### Requirement: ReasoningEngine 推理引擎
ReasoningEngine SHALL 从 POC 级别重构为生产级，增加完整的错误处理（每个阶段独立 try/except + 降级策略）、监控埋点（Langfuse trace + Prometheus 指标）、配置外部化（所有阈值通过 ReasoningSettings 环境变量配置）。五维度复杂度评估 SHALL 支持权重动态调整。模糊区间 LLM 兜底 SHALL 记录分类结果用于后续优化。

#### Scenario: 错误处理降级
- **WHEN** 复杂度评估过程中 LLM 调用失败
- **THEN** 系统 SHALL 降级为纯规则评估，记录 WARNING 日志，不影响请求处理

#### Scenario: 监控埋点
- **WHEN** ReasoningEngine.decide() 执行完成
- **THEN** SHALL 上报 Langfuse span（含 mode/complexity_score/duration）和 Prometheus 指标（reasoning_duration_seconds）

#### Scenario: 配置热更新
- **WHEN** 管理员修改 REASONING_FUZZY_ZONE_LOW 环境变量
- **THEN** 下次请求 SHALL 使用新阈值，无需重启服务

### Requirement: ExecutionPlan 资源获取
ExecutionPlan 的资源获取（_resolve_resources）SHALL 实现超时控制（总超时 10 秒）、并行获取（MCP/Skill/Memory 并行）、部分失败降级（某个资源获取失败不影响其他资源）。

#### Scenario: 并行资源获取
- **WHEN** 需要获取 MCP 工具、Skill 列表、用户记忆
- **THEN** 三者 SHALL 并行获取，总耗时取最长者而非累加

#### Scenario: 部分资源失败
- **WHEN** MCP 连接超时但 Skill 和 Memory 正常
- **THEN** 系统 SHALL 使用可用资源继续构建，MCP 工具列表为空
