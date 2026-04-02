## 1. 数据模型定义

- [x] 1.1 创建 `src/monitoring/pipeline_events.py`，定义 `EventStatus` 枚举（started/completed/failed）和 `PipelineEvent` dataclass（trace_id, request_id, session_id, step, status, timestamp, duration_ms, metadata）
- [x] 1.2 在 `PipelineEvent` 中实现 `to_log_string()` 方法，输出 `PIPELINE_EVENT | step=xxx status=xxx duration_ms=xxx ...` 格式
- [x] 1.3 定义 `StepStats` dataclass（count, avg_ms, p50_ms, p95_ms, p99_ms, max_ms, error_count, error_rate）

## 2. 核心记录器

- [x] 2.1 在 `pipeline_events.py` 中实现 `pipeline_step` 异步上下文管理器，自动记录 started/completed/failed 事件，支持 `add_metadata()` 追加数据
- [x] 2.2 实现 `log_pipeline_step` 装饰器，支持 sync/async 函数，内部复用 `pipeline_step`
- [x] 2.3 实现事件输出逻辑：通过 logging.info 输出结构化日志行，可选上报 Langfuse span
- [x] 2.4 实现步骤命名校验：非点分命名时记录 warning 但不阻断

## 3. 指标采集器

- [x] 3.1 创建 `src/monitoring/execution_metrics.py`，实现 `MetricsCollector` 单例，内部使用 `deque(maxlen=10000)` 环形缓冲
- [x] 3.2 实现 `record(event)` 方法，协程安全，耗时 <1ms，异常不中断业务
- [x] 3.3 实现 `get_step_stats(step, window_minutes)` 方法，计算耗时分布（avg/p50/p95/p99/max）和错误率
- [x] 3.4 实现 `get_trace_timeline(trace_id)` 方法，按 timestamp 升序返回事件列表
- [x] 3.5 实现 `get_overview(window_minutes)` 方法，返回所有步骤的 StepStats，按 avg_ms 降序

## 4. Gateway 层埋点

- [x] 4.1 在 `src/gateway/rest_api.py` 的 `submit_query()` 中添加 `gateway.receive` 事件
- [x] 4.2 在 `src/gateway/rest_api.py` 的 `_run_orchestration()` 完成时添加 `gateway.respond` 事件

## 5. Orchestrator 层埋点

- [x] 5.1 在 `src/orchestrator/orchestrator_agent.py` 的 `run_orchestrator()` 中为 `intent.classify` 步骤添加 `pipeline_step`
- [x] 5.2 为 `toolset.assemble` 步骤添加 `pipeline_step`
- [x] 5.3 为 `plan_and_decompose()` 添加 `orchestrator.plan` 事件，metadata 包含 task_count
- [x] 5.4 为 `_execute_agent()` 添加 `orchestrator.execute` 事件
- [x] 5.5 为 `execute_native_worker()` 添加 `worker.native.{type}` 事件，metadata 包含 worker_type 和 task_id
- [x] 5.6 为 `execute_sandbox_task()` 添加 `worker.sandbox` 事件
- [x] 5.7 为 `execute_skill()` 添加 `skill.execute.{name}` 事件

## 6. Worker 层埋点

- [x] 6.1 在 `src/workers/base.py` 的 `BaseWorker.execute()` 中集成 `pipeline_step`，记录 worker.native.{type} 事件
- [x] 6.2 在 `src/workers/sandbox/sandbox_worker.py` 中为沙箱创建添加 `worker.sandbox.create` 事件
- [x] 6.3 为沙箱命令执行添加 `worker.sandbox.execute` 事件
- [x] 6.4 为沙箱销毁添加 `worker.sandbox.destroy` 事件

## 7. Middleware 层埋点

- [x] 7.1 在 `src/middleware/pipeline.py` 的 `execute()` 中为 before_agent 阶段添加 `middleware.before` 事件
- [x] 7.2 为 after_agent 阶段添加 `middleware.after` 事件

## 8. 集成与连接

- [x] 8.1 在 `pipeline_step` 中自动调用 `MetricsCollector.record()` 完成事件采集
- [x] 8.2 在 `pipeline_step` 中集成 Langfuse 可选上报（检测 get_langfuse() 是否可用）
- [x] 8.3 扩展 `src/core/logging.py` 的 ContextVar，增加 `session_id_var` 供 PipelineEvent 自动获取上下文

## 9. 测试

- [x] 9.1 编写 `tests/test_pipeline_events.py`：测试 PipelineEvent 模型、pipeline_step 上下文管理器、log_pipeline_step 装饰器
- [x] 9.2 编写 `tests/test_execution_metrics.py`：测试 MetricsCollector 的 record、get_step_stats、get_trace_timeline、get_overview
- [x] 9.3 测试异常场景：事件记录失败不中断业务、缓冲区满自动淘汰、Langfuse 未配置时静默跳过
