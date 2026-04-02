## ADDED Requirements

### Requirement: PipelineEvent 数据模型
系统 SHALL 定义标准化的 PipelineEvent 数据模型，包含以下必填字段：
- `trace_id`: 全链路追踪 ID
- `request_id`: 请求 ID
- `session_id`: 会话 ID
- `step`: 步骤标识（点分层级命名，如 `gateway.receive`）
- `status`: 事件状态（`started` | `completed` | `failed`）
- `timestamp`: 事件发生时间戳
- `duration_ms`: 步骤耗时（仅 completed/failed 时有值）
- `metadata`: 步骤特定的附加数据字典

#### Scenario: 正常步骤记录完整事件
- **WHEN** 一个关键步骤（如 worker.execute）开始并成功完成
- **THEN** 系统 MUST 记录两条 PipelineEvent：一条 status=started，一条 status=completed 且包含 duration_ms

#### Scenario: 步骤失败记录错误事件
- **WHEN** 一个关键步骤执行失败抛出异常
- **THEN** 系统 MUST 记录 status=failed 的 PipelineEvent，metadata 中包含 `error_type` 和 `error_msg`，且包含 duration_ms

#### Scenario: 缺少上下文 ID 时降级
- **WHEN** ContextVar 中未设置 trace_id 或 request_id
- **THEN** 系统 MUST 使用空字符串作为默认值，不得抛出异常

### Requirement: pipeline_step 上下文管理器
系统 SHALL 提供 `pipeline_step` 异步上下文管理器，自动记录步骤的 started/completed/failed 事件。

#### Scenario: 使用上下文管理器记录步骤
- **WHEN** 业务代码使用 `async with pipeline_step("worker.native.rag") as event` 包裹执行逻辑
- **THEN** 进入时自动记录 started 事件，退出时自动记录 completed 事件（含 duration_ms），异常时记录 failed 事件

#### Scenario: 上下文管理器内追加 metadata
- **WHEN** 在 `pipeline_step` 块内调用 `event.add_metadata(key=value)`
- **THEN** 追加的 metadata MUST 出现在最终的 completed/failed 事件中

#### Scenario: 事件记录自身异常不影响业务
- **WHEN** PipelineEvent 记录过程中发生异常（如序列化失败）
- **THEN** 系统 MUST 捕获异常并记录 warning 日志，不得中断业务流程

### Requirement: log_pipeline_step 装饰器
系统 SHALL 提供 `log_pipeline_step` 装饰器，适用于整个函数即为一个步骤的场景。

#### Scenario: 装饰器自动记录函数执行事件
- **WHEN** 使用 `@log_pipeline_step("intent.classify")` 装饰一个 async 函数
- **THEN** 函数调用时自动记录 started 事件，返回时记录 completed 事件，异常时记录 failed 事件

#### Scenario: 装饰器支持同步和异步函数
- **WHEN** `@log_pipeline_step` 应用于同步函数
- **THEN** 系统 MUST 正确记录事件，不得要求函数必须是 async

### Requirement: 结构化日志输出
PipelineEvent MUST 通过 Python logging 输出为结构化日志行，格式为：
`PIPELINE_EVENT | step={step} status={status} duration_ms={duration_ms} {metadata_kv_pairs}`

#### Scenario: 事件输出为结构化日志
- **WHEN** 一个 PipelineEvent 被记录
- **THEN** 系统 MUST 通过 logging.info 输出包含 `PIPELINE_EVENT |` 前缀的结构化日志行，所有字段以 key=value 格式呈现

#### Scenario: 与现有日志格式兼容
- **WHEN** PipelineEvent 日志行被输出
- **THEN** 日志行 MUST 包含现有 StructuredFormatter 注入的 request_id 和 trace_id 前缀

### Requirement: Langfuse 可选上报
当 Langfuse 已配置时，PipelineEvent SHOULD 自动映射为 Langfuse span。

#### Scenario: Langfuse 已配置时自动上报
- **WHEN** Langfuse 客户端已初始化，且一个 PipelineEvent(status=completed) 被记录
- **THEN** 系统 MUST 创建对应的 Langfuse span，包含 step 名称、duration、metadata

#### Scenario: Langfuse 未配置时静默跳过
- **WHEN** Langfuse 客户端未配置（返回 None）
- **THEN** 系统 MUST 跳过 Langfuse 上报，仅输出本地日志，不得报错

### Requirement: 步骤命名规范
所有 step 标识 MUST 遵循点分层级命名规范：`{layer}.{action}` 或 `{layer}.{sublayer}.{action}`。

#### Scenario: 标准步骤名称
- **WHEN** 系统记录关键步骤事件
- **THEN** step 值 MUST 为以下之一：`gateway.receive`, `intent.classify`, `toolset.assemble`, `middleware.before`, `orchestrator.plan`, `orchestrator.execute`, `worker.native.{type}`, `worker.sandbox`, `skill.execute.{name}`, `middleware.after`, `gateway.respond`

#### Scenario: 非法步骤名称
- **WHEN** 传入不符合点分命名规范的 step 值
- **THEN** 系统 MUST 记录 warning 日志提示命名不规范，但仍正常记录事件
