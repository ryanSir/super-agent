## ADDED Requirements

### Requirement: LanceDB 三层记忆存储
系统 SHALL 使用 LanceDB 实现三层记忆存储：Profile（用户画像，结构化字段）、Facts（事实，带时间戳和来源）、Episodes（对话片段，带向量索引）。每层 SHALL 有独立的表和索引策略。

#### Scenario: Profile 存取
- **WHEN** 系统提取到用户角色信息 "数据科学家"
- **THEN** SHALL 更新 Profile 表的 role 字段，覆盖旧值

#### Scenario: Facts 存取
- **WHEN** 系统提取到事实 "用户偏好 Python"
- **THEN** SHALL 插入 Facts 表，包含 fact_text、source_session_id、created_at、confidence_score

#### Scenario: Episodes 向量检索
- **WHEN** 查询 "上次讨论的数据库方案"
- **THEN** SHALL 对 Episodes 表进行向量相似度检索，返回 top_k 最相关的对话片段

### Requirement: 语义召回
系统 SHALL 支持基于 Embedding 向量的语义检索，检索超时 SHALL 不超过 200ms，超时 SHALL 降级为空结果（不影响主流程）。

#### Scenario: 正常语义检索
- **WHEN** 收到用户查询，触发记忆检索
- **THEN** 系统 SHALL 将查询文本转为 Embedding，在 LanceDB 中检索 top_k 相关记忆，200ms 内返回

#### Scenario: 检索超时降级
- **WHEN** 语义检索耗时超过 200ms
- **THEN** 系统 SHALL 返回空结果，主流程继续执行，记录 WARNING 日志

#### Scenario: Embedding 服务不可用
- **WHEN** Embedding API 调用失败
- **THEN** 系统 SHALL 降级为关键词匹配检索，记录告警

### Requirement: 自动提取 + 去重 + 时间衰减
系统 SHALL 在对话结束后异步提取记忆（Profile 更新 + Facts 抽取），对重复 Facts 进行去重合并，对过期 Facts 进行时间衰减（降低 confidence_score）。

#### Scenario: 对话后自动提取
- **WHEN** 一轮对话结束
- **THEN** 系统 SHALL 异步调用 LLM 提取 Profile 更新和新 Facts，不阻塞响应返回

#### Scenario: 重复 Fact 去重
- **WHEN** 新提取的 Fact 与已有 Fact 语义相似度 > 0.9
- **THEN** 系统 SHALL 合并为一条，更新时间戳和 confidence_score

#### Scenario: 时间衰减
- **WHEN** 某条 Fact 超过 30 天未被访问
- **THEN** 系统 SHALL 将其 confidence_score 乘以衰减系数（默认 0.8）

### Requirement: autoDream 定期整合
系统 SHALL 支持定期整合碎片记忆为结构化摘要（autoDream），减少记忆碎片化。

#### Scenario: 触发整合
- **WHEN** 用户的 Facts 数量超过 100 条
- **THEN** 系统 SHALL 触发 autoDream，调用 LLM 将相关 Facts 整合为结构化摘要

#### Scenario: 整合后清理
- **WHEN** autoDream 生成摘要后
- **THEN** 被整合的原始 Facts SHALL 标记为 archived，不再参与检索，摘要作为新 Fact 存入

### Requirement: 多用户记忆隔离
系统 SHALL 按 user_id 隔离记忆数据，用户 A 的记忆 SHALL 不可被用户 B 访问。

#### Scenario: 跨用户隔离
- **WHEN** 用户 A 和用户 B 同时使用系统
- **THEN** 各自的 Profile/Facts/Episodes SHALL 完全隔离，检索时 SHALL 自动过滤 user_id

#### Scenario: 用户记忆删除
- **WHEN** 用户请求删除所有记忆
- **THEN** 系统 SHALL 删除该 user_id 下所有三层数据，操作不可逆，需二次确认