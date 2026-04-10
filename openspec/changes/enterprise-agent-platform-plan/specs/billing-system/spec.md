## ADDED Requirements

### Requirement: 三级用量追踪
系统 SHALL 实现 per-request / per-session / per-user 三级 token 用量追踪。每级 SHALL 独立统计 input_tokens、output_tokens、total_cost，支持实时查询。

#### Scenario: Request 级追踪
- **WHEN** 一次请求包含 3 次 LLM 调用
- **THEN** 系统 SHALL 汇总 3 次调用的 token 和成本，关联到该 request_id

#### Scenario: Session 级追踪
- **WHEN** 一个会话包含 5 次请求
- **THEN** 系统 SHALL 汇总 5 次请求的用量，关联到该 session_id

#### Scenario: User 级追踪
- **WHEN** 查询用户 A 的月度用量
- **THEN** 系统 SHALL 返回该用户所有会话的累计 token 和成本

### Requirement: 配额管理
系统 SHALL 支持 per-user 配额限制，包括：日 token 上限、月 token 上限、单次请求 token 上限。超过配额 SHALL 拒绝请求或降级到低成本模型。

#### Scenario: 配额检查
- **WHEN** 用户 A 的日 token 消耗达到配额 80%
- **THEN** 系统 SHALL 推送配额告警通知

#### Scenario: 配额超限
- **WHEN** 用户 A 的日 token 消耗达到 100%
- **THEN** 系统 SHALL 拒绝新请求并返回 "配额已用尽，请明日再试" 或降级到 fast_model

#### Scenario: 单次请求限制
- **WHEN** 单次请求预估 token 超过 100K
- **THEN** 系统 SHALL 提示用户简化请求或拆分任务

### Requirement: 用量报告
系统 SHALL 生成日 / 周 / 月用量报告，包括：总 token 消耗、成本明细（按模型分）、Top 用户排名、趋势图数据。

#### Scenario: 日报生成
- **WHEN** 每日 00:00
- **THEN** 系统 SHALL 自动生成前一天的用量报告，存入数据库

#### Scenario: 报告查询
- **WHEN** 管理员请求 2026 年 4 月的月报
- **THEN** 系统 SHALL 返回该月的汇总数据和趋势图数据（JSON 格式）
