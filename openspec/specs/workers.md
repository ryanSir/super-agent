# Workers 规格

## 架构

Workers 分为两类，按任务风险等级路由：

| 类型 | 目录 | 执行环境 | 适用场景 |
|------|------|---------|---------|
| Native Workers | `src/workers/native/` | 宿主进程内 | SAFE 级别：RAG、DB 查询、API 调用 |
| Sandbox Worker | `src/workers/sandbox/` | E2B 隔离沙箱 | DANGEROUS 级别：代码生成、脚本执行 |

## 接口契约

```python
class WorkerProtocol(Protocol):
    @property
    def name(self) -> str: ...
    async def execute(self, task: TaskNode) -> WorkerResult: ...
```

## BaseWorker 模板方法

所有 Native Worker 继承 `BaseWorker`，只需实现 `_do_execute`：

```python
class BaseWorker:
    async def execute(self, task: TaskNode) -> WorkerResult:
        # 1. 结构化日志
        # 2. Langfuse span 包裹
        # 3. 调用 _do_execute(task)
        # 4. 异常捕获 → 返回 WorkerResult(success=False, error=...)

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        raise NotImplementedError  # 子类实现
```

## 已实现 Native Workers

| Worker | 文件 | 注册 key |
|--------|------|---------|
| RAG 检索 | `src/workers/native/rag_worker.py` | `rag_worker` |
| DB 查询 | `src/workers/native/db_query_worker.py` | `db_query_worker` |
| API 调用 | `src/workers/native/api_call_worker.py` | `api_call_worker` |

## Sandbox Worker

- 文件：`src/workers/sandbox/sandbox_worker.py`
- 注册 key：`sandbox_worker`
- 接受 `SandboxTask`（非 `TaskNode`），由 Orchestrator 的 `execute_sandbox_task` tool 调用
- 内部通过 `sandbox_manager.py` 管理 E2B 实例生命周期
- 通过 `ipc.py` 将 JSONL IPC 消息转换为 A2UI 事件

## 关键约束

- DB Worker 只允许 SELECT 查询，禁止写操作
- Native Worker 在宿主进程内执行，不得运行不可信代码
- Sandbox Worker 每次任务创建独立 E2B 实例，任务完成后销毁
- 所有 Worker 执行结果统一返回 `WorkerResult`，通过 `success` 字段区分成功/失败
- BaseWorker 捕获所有非 `WorkerError` 异常，转换为 `WorkerResult(success=False)`

## Worker 执行日志

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

## 数据模型

```python
class TaskNode(BaseModel):
    task_id: str
    task_type: str      # rag_retrieval | db_query | api_call | sandbox_coding
    description: str
    input_data: Dict[str, Any]
    risk_level: RiskLevel  # SAFE | DANGEROUS

class WorkerResult(BaseModel):
    task_id: str
    success: bool
    data: Optional[Any]
    error: Optional[str]
    metadata: Dict[str, Any]
```
