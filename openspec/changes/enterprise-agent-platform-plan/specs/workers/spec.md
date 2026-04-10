## MODIFIED Requirements

### Requirement: Worker 健康检查与重试
所有 Worker SHALL 实现健康检查接口（health_check() → bool），支持定期探活。Worker 执行失败 SHALL 支持可配置的重试策略（最多 2 次，指数退避）。

#### Scenario: 健康检查
- **WHEN** 系统每 30 秒执行 Worker 健康检查
- **THEN** 不健康的 Worker SHALL 被标记为 unavailable，Agent 调用时返回友好错误

#### Scenario: 执行重试
- **WHEN** RAGWorker 执行因网络超时失败
- **THEN** 系统 SHALL 等待 1 秒后重试，第二次等待 2 秒，最多重试 2 次

#### Scenario: 重试耗尽
- **WHEN** Worker 重试 2 次仍失败
- **THEN** 系统 SHALL 返回最终错误，记录完整的重试链日志

### Requirement: Worker 指标上报
每个 Worker 执行 SHALL 上报 Prometheus 指标：worker_execution_duration_seconds（按 worker_type 标签）、worker_execution_total（成功/失败计数）、worker_active_count（当前活跃执行数）。

#### Scenario: 指标上报
- **WHEN** RAGWorker 执行完成
- **THEN** SHALL 上报 duration=1.2s, status=success 到 Prometheus

#### Scenario: 慢执行告警
- **WHEN** Worker 执行耗时超过 P95 的 2 倍
- **THEN** SHALL 记录 WARNING 日志并上报 slow_execution 指标

### Requirement: WebSearchWorker 多搜索引擎
WebSearchWorker SHALL 支持多个搜索引擎后端（百度/Google/Bing），通过配置切换。搜索结果 SHALL 统一为标准格式（title/url/snippet/source）。

#### Scenario: 搜索引擎切换
- **WHEN** 配置 WEB_SEARCH_ENGINE=google
- **THEN** WebSearchWorker SHALL 使用 Google 搜索 API

#### Scenario: 搜索引擎降级
- **WHEN** 主搜索引擎 API 不可用
- **THEN** 系统 SHALL 自动切换到备选搜索引擎

#### Scenario: 结果格式统一
- **WHEN** 不同搜索引擎返回不同格式的结果
- **THEN** WebSearchWorker SHALL 统一转换为标准格式输出
