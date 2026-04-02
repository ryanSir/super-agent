## Context

当前系统已有基础设施：
- `src/core/logging.py`：结构化日志，ContextVar 注入 request_id / trace_id
- `src/monitoring/langfuse_tracer.py`：Langfuse trace/span 上下文管理器
- `src/monitoring/otel_setup.py`：OTEL 导出到 Langfuse

现状问题：
1. 各模块日志格式不统一，`[Module] 描述 | key=value` 是约定但无强制保障
2. 缺少统一的事件模型——无法程序化地解析和聚合日志
3. 关键步骤的耗时统计分散在各处，没有集中的指标采集
4. 排查问题时需要手动 grep 多个模块日志，无法通过 trace_id 自动还原完整链路时间线

请求全链路：
```
Gateway.submit_query()
  → IntentRouter.classify()
  → ToolsetAssembler.assemble()
  → MiddlewarePipeline.execute()
    → before_agent (Token/Loop/Error/Memory middlewares)
    → Orchestrator._execute_agent()
      → plan_and_decompose() → planner_agent.run()
      → execute_native_worker() → BaseWorker.execute()
      → execute_sandbox_task() → SandboxWorker.execute()
      → execute_skill() → run_skill()
    → after_agent
  → Gateway 响应/流式输出
```

## Goals / Non-Goals

**Goals:**
- 定义标准化的 PipelineEvent 数据模型，所有关键步骤使用统一格式记录
- 提供零侵入的装饰器/上下文管理器，最小化对业务代码的改动
- 采集各步骤耗时、Token 消耗、成功/失败指标，支持按 trace_id/session_id 聚合
- 通过 trace_id 可还原完整请求执行时间线（事件序列 + 耗时瀑布图数据）

**Non-Goals:**
- 不替换现有 Langfuse/OTEL 集成
- 不引入新的外部存储（Prometheus/InfluxDB 等）
- 不做前端日志/埋点
- 不做日志持久化方案

## Decisions

### Decision 1: 统一事件模型 PipelineEvent

采用 Pydantic dataclass 定义标准事件：

```python
@dataclass
class PipelineEvent:
    trace_id: str           # 全链路追踪 ID
    request_id: str         # 请求 ID
    session_id: str         # 会话 ID
    step: str               # 步骤标识: gateway.receive, intent.classify, orchestrator.plan, worker.execute, ...
    status: EventStatus     # started | completed | failed
    timestamp: float        # time.time()
    duration_ms: float | None  # 仅 completed/failed 时有值
    metadata: dict          # 步骤特定数据（worker_type, skill_name, token_count, error_msg 等）
```

**为什么不用现有的 logging 格式？** 现有格式是人类可读的文本，无法程序化解析。PipelineEvent 是结构化数据，既输出为结构化日志行，也可直接用于指标聚合。

**为什么不直接扩展 Langfuse span？** Langfuse 是外部依赖，可能未配置或不可用。PipelineEvent 基于本地 logging，零外部依赖，Langfuse 作为可选的上报通道。

### Decision 2: 零侵入埋点方式 — 上下文管理器 + 装饰器

提供两种埋点方式：

```python
# 方式 1: 上下文管理器（适合需要在 block 内访问 event 的场景）
async with pipeline_step("worker.execute", metadata={"worker_type": "rag"}) as event:
    result = await worker.execute(task)
    event.add_metadata(result_count=len(result.data))

# 方式 2: 装饰器（适合整个函数就是一个步骤的场景）
@log_pipeline_step("intent.classify")
async def classify(self, query: str) -> IntentResult:
    ...
```

**为什么选上下文管理器而非 AOP/monkey-patch？** 显式优于隐式。上下文管理器在代码中可见，易于理解和调试，且不依赖框架魔法。

### Decision 3: 指标采集 — 内存环形缓冲 + 定期聚合

```python
class MetricsCollector:
    _events: deque[PipelineEvent]  # 固定大小环形缓冲，默认 10000 条

    def record(self, event: PipelineEvent) -> None: ...
    def get_step_stats(self, step: str, window_minutes: int = 5) -> StepStats: ...
    def get_trace_timeline(self, trace_id: str) -> list[PipelineEvent]: ...
```

**为什么用内存而非 Redis？** 指标采集是辅助功能，不应增加 Redis 负载。环形缓冲自动淘汰旧数据，内存占用可控（约 10000 × 200B ≈ 2MB）。需要持久化分析时，通过 Langfuse 上报。

**为什么不用 Prometheus？** 当前系统未引入 Prometheus，为了日志增强引入新的监控栈成本过高。后续如有需要可通过 OTEL exporter 桥接。

### Decision 4: 事件输出通道

PipelineEvent 同时输出到两个通道：
1. **结构化日志**（必选）：通过 logging 输出 JSON 格式事件行，与现有日志流合并
2. **Langfuse span**（可选）：如果 Langfuse 已配置，自动将事件映射为 span

日志输出格式：
```
2024-01-01 12:00:00 [INFO] [req=abc12345] [trace=def67890] PIPELINE_EVENT | step=worker.execute status=completed duration_ms=234 worker_type=rag
```

### Decision 5: 步骤命名规范

采用点分层级命名：`{layer}.{action}`

| 步骤 | step 值 |
|------|---------|
| 请求接入 | `gateway.receive` |
| 意图分类 | `intent.classify` |
| 工具集装配 | `toolset.assemble` |
| 中间件前置 | `middleware.before` |
| 任务规划 | `orchestrator.plan` |
| Agent 执行 | `orchestrator.execute` |
| Native Worker | `worker.native.{type}` |
| Sandbox Worker | `worker.sandbox` |
| Skill 执行 | `skill.execute.{name}` |
| 中间件后置 | `middleware.after` |
| 响应完成 | `gateway.respond` |

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 埋点代码增加各模块复杂度 | 上下文管理器封装，每个埋点仅 1-2 行代码 |
| 高并发下内存缓冲溢出 | 环形缓冲固定大小，自动淘汰；可通过配置调整 |
| 事件记录本身出错影响业务 | 所有事件记录包裹在 try/except 中，失败仅 warning 不中断 |
| JSON 日志行增加日志量 | 仅关键步骤记录（约 10 个/请求），非逐行代码级日志 |
| 与现有 Langfuse trace 重复 | PipelineEvent 是补充层，提供本地可用的结构化数据；Langfuse 可能未配置 |
