## Context

当前系统基于 pydantic-deep 框架构建 AI Agent，事件发布（tool_call、tool_result、thinking、text_stream、render_widget）分散在三处：

1. `gateway/rest_api.py` — `_run_agent()` 中 120+ 行内联推送，遍历 `agent.iter()` 的 node 类型手动提取和发布事件
2. `capabilities/base_tools.py` — `_wrap_with_tool_result()` 包装器通过 `ContextVar[publish_fn]` 注入发布函数，在工具执行后推送 tool_result
3. `orchestrator/hooks.py` — `create_event_push_hooks()` 本应通过框架 Hook 机制推送事件，但因与前两者重复而被禁用

此外，hooks.py 的审计 hook 存在并发 bug，token tracker 是空壳，所有 hook 行为硬编码无法配置。

pydantic-deep 框架提供了 `AbstractCapability` API（替代旧的 AgentMiddleware），支持完整的 Agent 生命周期拦截，是解决事件发布统一的正确抽象层。

## Goals / Non-Goals

**Goals:**
- 将事件发布统一到一个 `EventPublishingCapability`，消除三路重复
- 修复审计 hook 的并发 bug
- 清理死代码（禁用的 event push hooks、no-op token tracker）
- 为 hooks/capabilities 行为添加配置面
- 引入 ToolGuard 安全能力

**Non-Goals:**
- 不改变 SSE/Redis Stream 传输层
- 不改变前端事件消费格式
- 不实现完整的多租户权限系统
- 不重写 ContextManagerCapability 或 CostTracking（已由框架处理）

## Decisions

### Decision 1: 事件发布用 Capability 而非 Hook

**选择**: `AbstractCapability` 子类
**备选**: 改进现有 Hook（启用被禁用的 event push hooks）

**理由**:
- 事件发布需要 per-run 状态管理（`_reported_tool_ids` 去重集合、pending 追踪）
- 需要 `wrap_tool_execute()` 包装执行流（计时 + Langfuse span + 原子化发布 tool_call/tool_result）
- 需要 `after_model_request()` 访问完整的 `ModelResponse` 对象提取 thinking/text 内容
- Hook 的 `HookInput` 只提供 `tool_name`/`tool_input`/`tool_result` 字符串，粒度不够
- Capability 的 `wrap_tool_execute(handler)` 可以同时处理 before（tool_call 事件）和 after（tool_result 事件），保证原子性

### Decision 2: Langfuse tracing 整合到 EventPublishingCapability

**选择**: 在 `wrap_tool_execute()` 中同时创建 Langfuse span
**备选**: 单独创建 TracingCapability

**理由**:
- 当前 tracing 已经和事件发布混在 `_wrap_with_tool_result()` 中
- 两者共享相同的生命周期点（工具执行前后）
- 拆分为两个 Capability 会增加复杂度但收益不大（tracing 逻辑只有 ~10 行）
- 未来如果 tracing 需求增长，可以再拆分

### Decision 3: 审计 hook 用 LIFO 栈修复并发问题

**选择**: `dict[str, list[float]]` LIFO 栈
**备选 A**: 用 `tool_name + hash(tool_input)` 做复合 key
**备选 B**: 升级为 Capability 使用 `call.tool_call_id`

**理由**:
- 备选 A 对相同参数的并发调用仍然冲突
- 备选 B 改动过大，审计日志是典型的 Hook 场景（观察 + 日志）
- LIFO 栈简单可靠，框架按 LIFO 顺序分发 POST_TOOL_USE，时序正确

### Decision 4: 配置用 Pydantic BaseSettings 嵌套

**选择**: `HooksSettings` 嵌套到 `AppSettings`
**备选**: 独立配置文件

**理由**:
- 与现有配置模式一致（LLMSettings、RedisSettings 等都是嵌套 BaseSettings）
- 通过环境变量控制，适合容器化部署
- 默认值与当前硬编码行为一致，零配置即可运行

### Decision 5: 安全能力用框架内置 ToolGuard

**选择**: `pydantic_ai_shields.ToolGuard`
**备选**: 自定义 SecurityCapability

**理由**:
- ToolGuard 已提供 `blocked` + `require_approval` + `approval_callback` 完整功能
- 已在项目依赖中，无需额外安装
- 通过 `prepare_tools()` 过滤工具可见性 + `before_tool_execute()` 拦截执行，覆盖基本安全需求
- 自定义 Capability 在当前阶段过度设计

## Risks / Trade-offs

**[事件顺序变化]** → Capability 生命周期的事件触发时机可能与 rest_api 内联推送略有不同（如 thinking 事件的提取时机）。**缓解**: Phase 4 分步迁移，每步对比前端 SSE 事件流，确认事件完整性和顺序。

**[pydantic-deep 内置工具的 tool_result]** → 框架内置工具（write_todos、search_skills 等）不经过自定义工具函数，但 `wrap_tool_execute` 会拦截所有工具调用（包括内置工具）。**缓解**: 验证 Capability 的 `wrap_tool_execute` 确实覆盖框架内置工具。

**[emit_chart 特殊处理]** → `emit_chart` 工具需要额外推送 `render_widget` 事件。**缓解**: 在 `after_tool_execute` 中按 `tool_name == "emit_chart"` 分支处理，逻辑从 `_handle_emit_chart_result` 迁移。

**[ToolGuard 误拦截]** → 配置错误可能导致正常工具被拦截。**缓解**: 默认 `blocked_tools` 为空，仅在显式配置时生效。

## Migration Plan

6 个 Phase 按依赖顺序实施，每个 Phase 独立可部署：

1. **Phase 1** — 修复审计 hook 并发 bug（独立，无依赖）
2. **Phase 2** — 添加 HooksSettings 配置面（独立，无依赖）
3. **Phase 3** — 新建 EventPublishingCapability（依赖 Phase 2 的配置开关）
4. **Phase 4** — 迁移：移除 rest_api 内联推送 + base_tools wrapper + 死代码 hooks（依赖 Phase 3）
5. **Phase 5** — 移除 token tracker 空壳（独立）
6. **Phase 6** — 引入 ToolGuard（依赖 Phase 2 的配置）

**回滚策略**: 每个 Phase 是独立 commit。Phase 4 是最大风险点，如果事件流不完整，revert Phase 4 commit 即可恢复到 Phase 3 状态（新旧路径并存）。

## Open Questions

1. `wrap_tool_execute` 是否覆盖 pydantic-deep 框架内置工具（write_todos 等）？需要在 Phase 3 实现后验证。如果不覆盖，需要保留 `_flush_pending_tool_results` 的部分逻辑作为兜底。
2. ToolGuard 的 `approval_callback` 是否需要对接 WebSocket 双向通信实现人工审批？当前 Phase 6 仅实现 blocked 黑名单，approval 流程留作后续。
