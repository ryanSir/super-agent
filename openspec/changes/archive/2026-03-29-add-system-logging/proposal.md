## Why

当前系统虽然有基础的结构化日志（`core/logging.py`）和 Langfuse 追踪（`monitoring/langfuse_tracer.py`），但关键步骤的日志记录是零散的、非标准化的。排查问题时需要在多个模块间手动拼接日志，缺乏统一的事件模型和链路耗时统计，无法快速定位瓶颈或异常环节。随着新技术（MCP、Skills 动态加载等）不断引入，需要一套标准化的关键步骤日志体系来支撑问题定位和执行链路分析。

## What Changes

- 定义统一的 **Pipeline Event** 事件模型，覆盖请求全链路关键步骤（Gateway 接入 → Intent 路由 → Orchestrator 规划 → Worker 执行 → 响应输出）
- 在各关键模块埋点，自动记录标准化事件日志（步骤名称、耗时、输入输出摘要、错误信息）
- 新增 **执行指标采集**，统计各步骤耗时、Token 消耗、成功/失败率，支持按 session/request 维度聚合
- 提供链路回放能力：通过 trace_id 可还原完整的请求执行时间线
- 所有日志增强向后兼容，不影响现有 Langfuse/OTEL 集成，作为补充层存在

## Non-goals

- 不替换现有的 Langfuse 追踪和 OTEL 集成，而是在其基础上增强
- 不引入新的外部存储依赖（日志仍输出到 stdout，指标通过现有 Langfuse 上报）
- 不涉及前端日志或前端埋点
- 不做日志持久化存储方案（由运维层面的日志收集系统负责）

## Capabilities

### New Capabilities
- `pipeline-event-log`: 标准化的管道事件日志体系，定义统一事件模型，在关键步骤自动记录结构化事件（步骤名、耗时、上下文、错误），支持通过 trace_id 还原完整执行链路
- `execution-metrics`: 执行指标采集与统计，各步骤耗时分布、Token 消耗追踪、成功/失败率统计，支持按 session/request 维度聚合分析

### Modified Capabilities
- `orchestrator`: 在规划和调度环节增加标准化事件日志埋点
- `workers`: 在 Worker 执行前后增加事件日志和耗时统计

## Impact

- **核心模块改动**: `gateway/`, `orchestrator/`, `workers/`, `middleware/`, `skills/` 各增加事件埋点代码
- **新增模块**: `src/monitoring/pipeline_events.py`（事件模型与记录器）、`src/monitoring/execution_metrics.py`（指标采集）
- **现有代码**: `core/logging.py` 需扩展 ContextVar 支持更多上下文字段（如 step_name）
- **依赖**: 无新外部依赖，复用现有 logging + Langfuse 基础设施
- **性能**: 事件记录为异步/非阻塞，对请求延迟影响可忽略
