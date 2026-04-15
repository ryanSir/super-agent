## REMOVED Requirements

### Requirement: Middleware 基类定义
**Reason**: pydantic-ai 框架已原生提供 `AbstractCapability` API，完全替代了自定义 `AgentMiddleware` 基类。四个钩子（`before_agent`、`after_agent`、`on_tool_call`、`on_tool_error`）已被 Capability 生命周期方法覆盖。
**Migration**: 使用 `AbstractCapability` 子类替代 `AgentMiddleware` 子类。`before_agent` → `before_run`，`after_agent` → `after_run`，`on_tool_call` → `before_tool_execute`/`after_tool_execute`，`on_tool_error` → `on_tool_execute_error`。

### Requirement: MiddlewareContext 贯穿请求生命周期
**Reason**: pydantic-ai 的 `RunContext` + Capability 实例字段（通过 `for_run()` 隔离）替代了 `MiddlewareContext`。`session_id`/`trace_id` 通过 `ctx.deps.metadata` 传递，`token_usage` 由 `CostTracking` capability 管理。
**Migration**: 使用 `RunContext[deps]` 访问请求上下文，使用 Capability 实例字段管理 per-run 状态。

### Requirement: MiddlewarePipeline 按序执行
**Reason**: pydantic-ai 原生支持多 Capability 按注册顺序执行，洋葱模型通过 `wrap_run`/`wrap_tool_execute` 实现。无需自定义 Pipeline。
**Migration**: 通过 `create_deep_agent(capabilities=[...])` 按顺序注册 Capability，框架自动管理执行链。

### Requirement: Pipeline 配置化开关
**Reason**: 各 Capability 通过独立的环境变量开关控制（如 `EVENT_PUBLISHING_ENABLED`、`AUDIT_HOOKS_ENABLED`），比全局 pipeline 开关更细粒度。
**Migration**: 使用 `HooksSettings` 中的各项开关替代全局 `middleware.enabled`。

### Requirement: TokenUsageMiddleware 记录 token 用量
**Reason**: `CostTracking` capability（来自 `pydantic_ai_shields`）已通过 `cost_tracking=True` 启用，提供 token/USD 追踪。无需自定义 middleware。
**Migration**: 已由 `create_deep_agent(cost_tracking=True)` 自动处理。

### Requirement: LoopDetectionMiddleware 检测重复 tool 调用
**Reason**: 已迁移为 pydantic-deep Hook（`create_loop_detection_hooks()`），功能完全一致。
**Migration**: 已实现在 `orchestrator/hooks.py`，通过 `PRE_TOOL_USE` + `BEFORE_RUN` hook 事件驱动。

### Requirement: ToolErrorHandlingMiddleware 捕获 tool 异常
**Reason**: pydantic-ai 框架原生处理工具异常（转为 `ToolReturnPart` 返回给 Agent），无需额外 middleware。`EventPublishingCapability.on_tool_execute_error` 负责发布错误事件。
**Migration**: 框架默认行为 + `on_tool_execute_error` Capability 方法。

### Requirement: MemoryMiddleware 异步更新记忆
**Reason**: pydantic-deep 框架提供 `MemoryCapability`（通过 `include_memory=True` 启用），当前系统使用自定义 `MemoryRetriever`，不走 middleware 路径。
**Migration**: 记忆更新通过 `recall_memory` 工具函数和 `MemoryRetriever` 直接处理。

### Requirement: SummarizationMiddleware 压缩长对话
**Reason**: `ContextManagerCapability`（来自 `pydantic_ai_summarization`）已通过 `context_manager=True` 启用，提供自动对话压缩。
**Migration**: 已由 `create_deep_agent(context_manager=True, context_manager_max_tokens=200_000)` 自动处理。
