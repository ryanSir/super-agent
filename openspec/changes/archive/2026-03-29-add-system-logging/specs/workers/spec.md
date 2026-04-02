## MODIFIED Requirements

### Requirement: Worker 执行日志标准化
BaseWorker.execute() SHALL 使用 `pipeline_step` 上下文管理器替代现有的手动日志记录，输出标准化 PipelineEvent。

#### Scenario: Native Worker 执行事件
- **WHEN** 任意 Native Worker（RAGWorker, DBQueryWorker, APICallWorker）的 `execute()` 被调用
- **THEN** 系统 MUST 记录 `worker.native.{type}` 的 started/completed/failed 事件，其中 type 为 worker 类型标识（rag, db_query, api_call）

#### Scenario: Worker 执行成功时记录结果摘要
- **WHEN** Worker 执行成功返回 WorkerResult(success=True)
- **THEN** completed 事件的 metadata MUST 包含 `worker_type` 和 `result_summary`（结果数据的简要描述，如数据条数）

#### Scenario: Worker 执行失败时记录错误详情
- **WHEN** Worker 执行失败（异常或 WorkerResult(success=False)）
- **THEN** failed 事件的 metadata MUST 包含 `worker_type`、`error_type`、`error_msg`

### Requirement: SandboxWorker 子步骤日志
SandboxWorker.execute() SHALL 在关键子步骤记录事件，提供沙箱执行的细粒度可观测性。

#### Scenario: 沙箱创建事件
- **WHEN** SandboxWorker 创建 E2B 沙箱环境
- **THEN** 系统 MUST 记录 `worker.sandbox.create` 事件，metadata 包含 sandbox 配置信息

#### Scenario: 沙箱命令执行事件
- **WHEN** SandboxWorker 在沙箱内执行命令
- **THEN** 系统 MUST 记录 `worker.sandbox.execute` 事件，metadata 包含命令摘要和执行耗时

#### Scenario: 沙箱销毁事件
- **WHEN** SandboxWorker 销毁沙箱环境
- **THEN** 系统 MUST 记录 `worker.sandbox.destroy` 事件

#### Scenario: 沙箱创建超时
- **WHEN** E2B 沙箱创建超过 30 秒未完成
- **THEN** 系统 MUST 记录 `worker.sandbox.create` 的 failed 事件，metadata 包含 `error_type=timeout`

### Requirement: Worker 日志与现有 Langfuse 追踪共存
Worker 的 PipelineEvent 记录 MUST 与 BaseWorker 中现有的 Langfuse observation_span 共存，不得替换或干扰现有追踪。

#### Scenario: 双通道记录
- **WHEN** Worker 执行且 Langfuse 已配置
- **THEN** 系统 MUST 同时产生 PipelineEvent 日志和 Langfuse span，两者独立运行

#### Scenario: Langfuse 未配置时仅记录事件
- **WHEN** Worker 执行且 Langfuse 未配置
- **THEN** 系统 MUST 仅记录 PipelineEvent 到本地日志，不报错
