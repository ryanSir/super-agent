### Requirement: MemoryStorage 抽象接口
系统 SHALL 提供 `MemoryStorage` 抽象基类，定义 `load`、`save`、`delete` 三个 async 方法。MUST 位于 `src/memory/storage.py`。

#### Scenario: 自定义存储后端
- **WHEN** 开发者实现 `MemoryStorage` 子类并注册到配置
- **THEN** 记忆系统使用该子类进行数据持久化

#### Scenario: 存储后端不可用
- **WHEN** Redis 连接失败
- **THEN** `load` 方法 MUST 返回空记忆结构，不抛出异常

### Requirement: RedisMemoryStorage 实现
系统 SHALL 提供 `RedisMemoryStorage` 作为默认存储实现，使用 Redis Hash 存储用户画像，Redis Sorted Set 存储事实记录。Key 格式：`memory:{user_id}:profile`、`memory:{user_id}:facts`。

#### Scenario: 保存用户画像
- **WHEN** 调用 `save(user_id, memory_data)` 且 memory_data 包含 profile 字段
- **THEN** profile 数据写入 `memory:{user_id}:profile` Hash，`updated_at` 字段更新为当前时间

#### Scenario: 加载用户记忆
- **WHEN** 调用 `load(user_id)` 且 Redis 中存在该用户数据
- **THEN** 返回包含 profile 和 facts 的完整记忆结构

#### Scenario: 用户无历史记忆
- **WHEN** 调用 `load(user_id)` 且 Redis 中无该用户数据
- **THEN** 返回空记忆结构 `{ profile: {}, facts: [], updated_at: null }`

### Requirement: 记忆数据结构
系统 SHALL 定义标准记忆数据结构，包含三个层级：
- `profile`: 用户画像（work_context、personal_context、top_of_mind），每个字段为摘要文本
- `facts`: 事实列表，每条包含 `content`（文本）、`created_at`（时间戳）、`source_session_id`（来源会话）
- `updated_at`: 最后更新时间

#### Scenario: 事实数量上限
- **WHEN** 用户的 facts 数量达到上限（默认 100 条）
- **THEN** 新增 fact 时 MUST 淘汰最旧的记录（按 created_at 排序）

#### Scenario: 事实去重
- **WHEN** 新提取的 fact 与已有 fact 内容相同（忽略首尾空格）
- **THEN** MUST 更新已有 fact 的时间戳，不重复添加

### Requirement: MemoryUpdater 异步更新记忆
系统 SHALL 提供 `MemoryUpdater` 类，接收对话内容，使用 LLM 提取用户画像更新和新事实，写入存储。更新过程 MUST 异步执行，不阻塞主请求。MUST 位于 `src/memory/updater.py`。

#### Scenario: 从对话提取事实
- **WHEN** 用户对话中提到 "我是数据科学家，主要做日志分析"
- **THEN** updater 使用 LLM 提取 fact: "用户是数据科学家，专注于日志分析领域"，并更新 profile.work_context

#### Scenario: 对话无有价值信息
- **WHEN** 用户对话仅包含简单的代码修改请求，无个人信息
- **THEN** updater MUST 不更新记忆，避免写入噪声数据

#### Scenario: LLM 提取失败
- **WHEN** LLM 调用超时或返回无效格式
- **THEN** updater MUST 记录错误日志，跳过本次更新，不影响后续请求

#### Scenario: 并发更新同一用户
- **WHEN** 两个会话同时触发同一用户的记忆更新
- **THEN** 系统 MUST 通过 Redis 分布式锁保证更新串行化，避免数据覆盖

### Requirement: MemoryRetriever 检索记忆
系统 SHALL 提供 `MemoryRetriever` 类，根据当前查询检索相关记忆，格式化为可注入 system prompt 的文本。MUST 位于 `src/memory/retriever.py`。

#### Scenario: 注入用户画像
- **WHEN** 用户发起新请求，且存在历史记忆
- **THEN** retriever 将 profile 摘要格式化为 `[User Context] ...` 文本，注入 Orchestrator system prompt

#### Scenario: 无历史记忆
- **WHEN** 新用户首次使用，无任何记忆数据
- **THEN** retriever 返回空字符串，不注入任何内容

#### Scenario: 检索超时降级
- **WHEN** Redis 查询超时（> 200ms）
- **THEN** retriever MUST 返回空字符串，记录警告日志，不阻塞请求

### Requirement: MemoryUpdateQueue 防抖队列
系统 SHALL 提供 `MemoryUpdateQueue`，对同一用户的多次更新请求进行防抖合并。在防抖窗口（默认 5 秒）内的多次提交 MUST 合并为一次 LLM 调用。

#### Scenario: 防抖合并
- **WHEN** 同一用户在 3 秒内触发 3 次记忆更新
- **THEN** 队列将 3 次对话内容合并，仅触发 1 次 LLM 提取调用

#### Scenario: 超过防抖窗口
- **WHEN** 同一用户的两次更新间隔超过 5 秒
- **THEN** 分别触发 2 次独立的 LLM 提取调用

### Requirement: Memory 配置
系统 SHALL 在 `MemorySettings` 中提供以下配置项：`enabled`（是否启用，默认 true）、`max_facts`（事实上限，默认 100）、`debounce_seconds`（防抖窗口，默认 5）、`update_model`（更新用 LLM 模型，默认 "fast"）。

#### Scenario: 禁用记忆系统
- **WHEN** 配置 `memory.enabled=false`
- **THEN** MemoryMiddleware 跳过所有操作，MemoryRetriever 返回空字符串

#### Scenario: 自定义事实上限
- **WHEN** 配置 `memory.max_facts=50`
- **THEN** 用户 facts 超过 50 条时触发淘汰
