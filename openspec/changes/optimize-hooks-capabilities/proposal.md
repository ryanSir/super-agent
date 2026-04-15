## Why

当前系统的事件发布逻辑分散在三处（`rest_api.py` 内联推送 120+ 行、`base_tools.py` ContextVar + wrapper、`hooks.py` 被禁用的 event push hooks），导致维护困难、职责不清。同时 hooks.py 存在审计 hook 并发 bug、token tracker 空壳、无配置化等问题。需要统一事件发布路径，修复已知缺陷，引入框架最佳实践。

## Non-goals

- 不重写 SSE/Redis Stream 传输层（streaming 模块保持不变）
- 不改变前端事件消费协议（事件格式兼容）
- 不实现完整的多租户权限系统（仅引入基础 ToolGuard）
- 不迁移 ContextManagerCapability 和 CostTracking（已由框架处理）

## What Changes

- **新建 `EventPublishingCapability`**：基于 `AbstractCapability` 的自定义 Capability，通过 `wrap_tool_execute` / `after_model_request` / `after_run` 统一接管所有事件发布（tool_call、tool_result、thinking、text_stream、render_widget）
- **修复审计 Hook 并发 bug**：`call_start_times` 从 `dict[str, float]` 改为 `dict[str, list[float]]`（LIFO 栈），解决并发调用同名工具时 start time 互相覆盖的问题
- **移除事件发布旧路径**：删除 `rest_api.py` 中 `_run_agent()` 的内联事件推送（~130 行）、`base_tools.py` 的 `_wrap_with_tool_result()` + ContextVar 模式、`hooks.py` 被禁用的 event push hooks
- **移除 Token Tracker 空壳**：`create_token_tracker_hooks()` 是 no-op，`CostTracking` capability 已覆盖此功能
- **添加配置面**：新增 `HooksSettings` 到 `AppSettings`，支持循环检测阈值、审计开关、事件发布开关、安全工具黑名单等环境变量配置
- **引入 ToolGuard 安全能力**：使用 `pydantic_ai_shields.ToolGuard` 实现配置化的工具黑名单拦截
- **BREAKING**：`agent-middleware.md` 旧规格中的 `AgentMiddleware` / `MiddlewarePipeline` 模型已被框架 Capabilities API 替代，规格需要更新为基于 Hooks + Capabilities 的新架构

## Capabilities

### New Capabilities
- `event-publishing`: 统一事件发布 Capability，替代三处分散的事件推送逻辑，基于 AbstractCapability 生命周期方法实现
- `hooks-config`: Hooks 配置化能力，通过 HooksSettings 控制各类 hook 的启用/参数

### Modified Capabilities
- `agent-middleware`: 旧的 AgentMiddleware/MiddlewarePipeline 规格需要更新，反映已迁移到 pydantic-ai Capabilities API + Hooks 的现状

## Impact

- **核心文件变更**：`orchestrator/hooks.py`、`orchestrator/agent_factory.py`、`gateway/rest_api.py`、`capabilities/base_tools.py`、`config/settings.py`
- **新增文件**：`capabilities/event_publishing.py`
- **删除代码**：~200 行（rest_api 内联推送 + base_tools wrapper + 死代码 hooks）
- **依赖**：`pydantic_ai_shields`（ToolGuard，已在项目依赖中）
- **前端兼容**：事件格式不变，SSE 通道不变，前端无需改动