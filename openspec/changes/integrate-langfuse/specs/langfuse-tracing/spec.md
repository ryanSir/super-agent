## ADDED Requirements

### Requirement: Langfuse 客户端初始化
系统 SHALL 在应用启动时根据 `LANGFUSE_ENABLED` 环境变量决定是否初始化 Langfuse 客户端。客户端使用 `LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_HOST` 配置连接。

#### Scenario: 启用 Langfuse 且配置正确
- **WHEN** `LANGFUSE_ENABLED=true` 且 public_key、secret_key、host 均已配置
- **THEN** 系统初始化 Langfuse 客户端并记录 info 日志 "Langfuse 初始化完成"

#### Scenario: 未启用 Langfuse
- **WHEN** `LANGFUSE_ENABLED=false` 或未设置
- **THEN** 所有追踪函数为 no-op，不初始化客户端，不产生任何网络请求

#### Scenario: 启用但连接失败
- **WHEN** `LANGFUSE_ENABLED=true` 但 Langfuse 服务不可达
- **THEN** 系统记录 warning 日志，Agent 执行流程不受影响，追踪数据静默丢弃

### Requirement: 请求级 Trace 创建
系统 SHALL 在每次 Agent 请求入口（`_execute_plan`）创建一个 Langfuse Trace，关联 session_id 和 trace_id。

#### Scenario: 正常请求创建 Trace
- **WHEN** 用户发起 Agent 查询请求
- **THEN** 系统创建 Trace，包含 name="agent_query"、session_id、trace_id，metadata 包含执行模式（mode）和原始 query

#### Scenario: Langfuse 未启用时请求
- **WHEN** Langfuse 未启用，用户发起 Agent 查询请求
- **THEN** 不创建 Trace，请求正常执行，无额外开销

### Requirement: 推理分类 Span 追踪
系统 SHALL 在推理引擎分类调用时创建 Span，记录复杂度评估结果和模式决策。

#### Scenario: 推理分类执行
- **WHEN** `reasoning_engine.decide()` 执行复杂度分类
- **THEN** 创建 Span name="reasoning_classify"，输出包含 complexity_level、suggested_mode、score

#### Scenario: 推理分类超时
- **WHEN** LLM 分类调用超时（超过 `REASONING_LLM_CLASSIFY_TIMEOUT`）
- **THEN** Span 记录 level="ERROR"，status_message 包含超时信息

### Requirement: 工具调用 Span 追踪
系统 SHALL 在每次工具调用时创建 Span，记录工具名称、输入参数、输出结果和执行耗时。

#### Scenario: 工具调用成功
- **WHEN** Agent 调用工具（如 web_search、db_query）并成功返回
- **THEN** 创建 Span name="tool_{tool_name}"，input 包含工具参数，output 包含 WorkerResult，level="DEFAULT"

#### Scenario: 工具调用失败
- **WHEN** 工具调用抛出异常或返回 success=false
- **THEN** Span 记录 level="ERROR"，status_message 包含错误信息

#### Scenario: 工具调用超时
- **WHEN** 工具执行超过配置的超时时间
- **THEN** Span 记录 level="ERROR"，status_message="timeout"，end_time 为超时时刻

### Requirement: LLM 调用 Generation 追踪
系统 SHALL 在每次 LLM 请求时创建 Generation，记录模型名称、Token 用量（input_tokens、output_tokens）、请求耗时。

#### Scenario: LLM 调用成功
- **WHEN** PydanticAI Agent 向 LLM 发起请求并收到响应
- **THEN** 创建 Generation，包含 model 名称、usage（prompt_tokens、completion_tokens）、latency

#### Scenario: LLM 调用失败
- **WHEN** LLM 请求返回错误（如 rate limit、timeout）
- **THEN** Generation 记录 level="ERROR"，status_message 包含错误类型

### Requirement: 应用关闭时 Flush
系统 SHALL 在应用关闭时调用 `langfuse.flush()` 确保所有追踪数据发送完毕。

#### Scenario: 正常关闭
- **WHEN** 应用收到关闭信号，lifespan 执行清理
- **THEN** 调用 `flush()` 等待所有缓冲数据发送完成后再关闭

#### Scenario: Flush 超时
- **WHEN** `flush()` 执行超过 5 秒
- **THEN** 记录 warning 日志，不阻塞应用关闭流程

### Requirement: 追踪上下文传递
系统 SHALL 通过 `langfuse_context` 在调用链中自动传递追踪上下文，确保 Trace → Span → Generation 的父子关系正确。

#### Scenario: 嵌套调用链
- **WHEN** 一次请求经过 reasoning → execute_plan → tool_call → llm_call
- **THEN** 所有 Span 和 Generation 正确嵌套在同一个 Trace 下，父子关系完整

#### Scenario: 并发工具调用
- **WHEN** Agent 同时调用多个工具（并发执行）
- **THEN** 每个工具调用创建独立的 Span，均挂载在同一个父 Span 下，互不干扰
