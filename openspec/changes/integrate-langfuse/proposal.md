## Why

项目已有 Langfuse 客户端骨架（`monitoring/langfuse_tracer.py`）和配置项（`LangfuseSettings`），但未实际接入 Agent 执行链路。当前 PydanticAI Agent 的 LLM 调用、工具执行、推理决策等关键路径完全没有可观测性，无法追踪请求耗时、Token 消耗和执行链路。需要将 Langfuse 全链路追踪真正接入 Agent 运行时，使用用户提供的 stage 环境 Key 连接 `https://stage-langfuse.patsnap.info`。

## What Changes

- 升级 `langfuse` 依赖版本，统一 `requirements.txt` 和 `pyproject.toml`
- 增强 `langfuse_tracer.py`：基于 `@observe()` 装饰器实现自动追踪，支持 Trace → Span → Generation 三层结构
- 在 Agent 执行主链路（`rest_api._execute_plan`）接入 Trace，自动关联 session_id / trace_id
- 在推理引擎（`reasoning_engine.py` 分类调用）接入 Span 追踪
- 在工具执行层接入 Span，记录每次工具调用的输入输出和耗时
- 在 `llm/config.py` 模型工厂层接入 Generation 追踪，记录 LLM 请求的 Token 用量
- `.env` 中添加 `LANGFUSE_ENABLED=true` 激活追踪
- 确保应用关闭时正确 flush 所有追踪数据

### Non-goals

- 不改造前端，不在 UI 上展示 Langfuse 数据
- 不引入 OpenTelemetry / Logfire 等额外追踪框架
- 不修改现有 Agent 执行逻辑和业务流程
- 不做自定义 Dashboard 或告警规则配置

## Capabilities

### New Capabilities

- `langfuse-tracing`: Langfuse 全链路追踪能力 — 覆盖 Agent 编排、LLM 调用、工具执行三层，自动采集 Trace/Span/Generation

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

- 依赖变更：`langfuse` 版本升级统一
- 代码变更：`monitoring/langfuse_tracer.py`（增强）、`gateway/rest_api.py`（接入 Trace）、`orchestrator/reasoning_engine.py`（接入 Span）、`capabilities/base_tools.py`（工具 Span）、`llm/config.py`（Generation 追踪）
- 配置变更：`.env` 新增 `LANGFUSE_ENABLED=true`
- 运行时影响：启用后每次请求会异步上报追踪数据到 Langfuse，网络开销极小（异步批量发送）