## Context

项目使用 PydanticAI 作为 Agent 框架，通过 `orchestrator/reasoning_engine.py` 做复杂度评估和模式路由，`gateway/rest_api.py` 驱动 Agent 迭代执行，`llm/config.py` 创建模型实例。现有 `monitoring/langfuse_tracer.py` 提供了 Langfuse 客户端懒初始化和基础 `create_trace` / `flush` 函数，但未接入任何实际执行链路。`.env` 中已配置 stage 环境的 Key，缺少 `LANGFUSE_ENABLED=true` 开关。

依赖版本不一致：`requirements.txt` 声明 `langfuse==4.0.1`，`pyproject.toml` 声明 `langfuse = "^2.55"`。

## Goals / Non-Goals

**Goals:**
- 将 Langfuse 追踪接入 Agent 执行全链路：请求入口 → 推理决策 → LLM 调用 → 工具执行
- 使用 Langfuse `@observe()` 装饰器实现自动化追踪，减少手动埋点
- 追踪数据包含：session_id、trace_id、执行模式、Token 用量、工具调用耗时
- 启用后连接 `https://stage-langfuse.patsnap.info`

**Non-Goals:**
- 不引入 OpenTelemetry / Logfire 等额外追踪框架
- 不改造前端 UI
- 不修改 Agent 执行逻辑

## Decisions

### 1. 使用 Langfuse `@observe()` 装饰器 vs 手动 Span 管理

**选择：`@observe()` 装饰器为主，关键路径手动补充**

- `@observe()` 自动捕获函数输入输出、耗时，代码侵入性最小
- 对于 PydanticAI Agent 迭代循环内部（`async for node in run`），装饰器无法直接包裹，需要在 `_execute_plan` 入口创建 Trace，内部通过 `langfuse_context` 传递
- 替代方案：全手动 `client.trace()` / `client.span()` — 代码侵入大，维护成本高，放弃

### 2. 追踪层级结构

```
Trace (per request)
├── Span: reasoning_classify (推理分类)
├── Span: execute_plan (Agent 执行)
│   ├── Generation: llm_call (每次 LLM 请求)
│   └── Span: tool_call (每次工具调用)
│       └── Span: worker_execute (Worker 执行)
└── metadata: session_id, mode, query
```

- Trace 在 `rest_api.py` 请求入口创建，绑定 session_id 和 trace_id
- Generation 在 `llm/config.py` 模型层自动采集（通过 Langfuse 的 PydanticAI 集成或手动包装）
- 工具 Span 在 `base_tools.py` 工具执行时创建

### 3. Langfuse 版本：统一到最新稳定版

**选择：统一 `langfuse>=2.55,<3.0`**

- `requirements.txt` 中的 `4.0.1` 疑似误写（Langfuse Python SDK 当前主线为 2.x），统一到 `^2.55`
- 2.x 版本支持 `@observe()` 装饰器和 `langfuse_context`，功能完备

### 4. 追踪开关与降级策略

- 通过 `LANGFUSE_ENABLED=true` 环境变量控制
- 未启用时所有追踪函数为 no-op，零开销
- Langfuse 服务不可达时，SDK 内部异步队列会静默丢弃，不阻塞主流程
- 在 `langfuse_tracer.py` 中提供统一的装饰器包装，未启用时直接透传原函数

## Risks / Trade-offs

- **[异步上报延迟]** → Langfuse SDK 使用后台线程批量发送，对请求延迟影响 <1ms。应用关闭时 `flush()` 已在 lifespan 中调用。
- **[SDK 版本冲突]** → 统一到 `^2.55`，与 PydanticAI 无直接依赖冲突。CI 中验证依赖解析。
- **[Langfuse 服务宕机]** → SDK 内置重试和静默降级，不影响 Agent 执行。日志中会有 warning。
- **[追踪数据量]** → 每次请求产生 1 Trace + N Spans，stage 环境数据量可控。生产环境可通过采样率控制。
