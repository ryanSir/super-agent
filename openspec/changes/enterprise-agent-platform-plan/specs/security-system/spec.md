## ADDED Requirements

### Requirement: 工具级权限模型
系统 SHALL 实现三态权限模型（allow / deny / ask），每个工具 SHALL 可配置独立的权限策略。deny 的工具 SHALL 对 Agent 不可见，ask 的工具 SHALL 在执行前请求用户确认。

#### Scenario: allow 权限
- **WHEN** Agent 调用权限为 allow 的工具（如 execute_rag_search）
- **THEN** 系统 SHALL 直接执行，不需要用户确认

#### Scenario: deny 权限
- **WHEN** 工具权限配置为 deny
- **THEN** 该工具 SHALL 不出现在 Agent 的可用工具列表中

#### Scenario: ask 权限
- **WHEN** Agent 调用权限为 ask 的工具（如 execute_db_query）
- **THEN** 系统 SHALL 暂停执行，推送确认请求到前端，用户批准后继续

#### Scenario: 权限配置持久化
- **WHEN** 管理员修改工具权限配置
- **THEN** 配置 SHALL 持久化到数据库，重启后生效

### Requirement: Prompt 注入检测
系统 SHALL 实现双层 Prompt 注入检测：规则层（正则匹配已知注入模式）+ LLM 层（调用 fast_model 判断可疑输入）。检测到注入 SHALL 拒绝请求并记录安全事件。

#### Scenario: 规则层检测
- **WHEN** 用户输入包含 "ignore previous instructions" 或 "system prompt:"
- **THEN** 系统 SHALL 标记为疑似注入，触发 LLM 层二次判断

#### Scenario: LLM 层确认
- **WHEN** 规则层标记疑似注入
- **THEN** 系统 SHALL 调用 fast_model 判断是否为真实注入，确认后拒绝请求

#### Scenario: 误报处理
- **WHEN** 正常技术讨论中包含 "system prompt" 关键词
- **THEN** LLM 层 SHALL 判断为非注入，允许请求继续

### Requirement: 审计日志
系统 SHALL 记录所有工具调用的审计日志，包括：调用者（user_id / agent_id）、工具名称、输入参数（脱敏）、输出摘要、执行时间、结果状态。日志 SHALL 支持按时间范围和用户查询。

#### Scenario: 工具调用审计
- **WHEN** Agent 调用 execute_db_query
- **THEN** 系统 SHALL 记录审计日志：who(user_id)、what(execute_db_query)、when(timestamp)、input(SQL脱敏)、output(行数)、duration(ms)

#### Scenario: 敏感参数脱敏
- **WHEN** 审计日志包含 API Key 或密码
- **THEN** 系统 SHALL 自动脱敏为 "***"，不记录明文

#### Scenario: 审计日志查询
- **WHEN** 管理员查询某用户过去 7 天的工具调用记录
- **THEN** 系统 SHALL 返回按时间排序的审计日志列表

### Requirement: SQL 白名单
系统 SHALL 对 DB Worker 的 SQL 查询实施白名单策略，仅允许 SELECT 语句，禁止 INSERT / UPDATE / DELETE / DROP / ALTER 等写操作。

#### Scenario: SELECT 允许
- **WHEN** Agent 提交 "SELECT * FROM users WHERE id = 1"
- **THEN** 系统 SHALL 允许执行

#### Scenario: 写操作拒绝
- **WHEN** Agent 提交 "DROP TABLE users"
- **THEN** 系统 SHALL 拒绝执行并返回 "仅允许 SELECT 查询"

#### Scenario: SQL 注入防护
- **WHEN** 查询包含 "1; DROP TABLE users--"
- **THEN** 系统 SHALL 检测到多语句注入，拒绝执行
