## 1. 配置面（Phase 2）

- [x] 1.1 在 `src_deepagent/config/settings.py` 中新增 `HooksSettings` 类（loop_window_size、loop_warn_threshold、loop_hard_limit、audit_enabled、event_publishing_enabled、blocked_tools 字段），添加到 `AppSettings.hooks`

## 2. 修复审计 Hook 并发 Bug（Phase 1）

- [x] 2.1 在 `src_deepagent/orchestrator/hooks.py` 的 `create_audit_hooks()` 中，将 `call_start_times: dict[str, float]` 改为 `dict[str, list[float]]`（LIFO 栈），更新 `log_call`（append）、`log_result`（pop）、`log_failure`（pop）

## 3. 清理 hooks.py 死代码（Phase 5 + 部分 Phase 4f）

- [x] 3.1 在 `src_deepagent/orchestrator/hooks.py` 中移除 `create_token_tracker_hooks()` 函数
- [x] 3.2 在 `src_deepagent/orchestrator/hooks.py` 中移除 `create_event_push_hooks()` 函数
- [x] 3.3 更新 `create_hooks()` 函数：移除 `publish_fn` 参数，从 settings 读取配置，按开关决定是否注册审计 hook，传入循环检测参数

## 4. 新建 EventPublishingCapability（Phase 3）

- [x] 4.1 创建 `src_deepagent/capabilities/event_publishing.py`，定义 `EventPublishingCapability(AbstractCapability)` 类，包含 `publish_fn`、`session_id`、`trace_id` 字段和 `_reported_tool_ids` per-run 状态
- [x] 4.2 实现 `before_run()` — 重置 `_reported_tool_ids`
- [x] 4.3 实现 `wrap_tool_execute()` — 发布 `tool_call` 事件 + 创建 Langfuse span + 调用 handler + 计时
- [x] 4.4 实现 `after_tool_execute()` — 发布 `tool_result` 事件 + 更新 Langfuse span + emit_chart 的 `render_widget` 特殊处理
- [x] 4.5 实现 `on_tool_execute_error()` — 发布 error 状态的 `tool_result` 事件 + 更新 Langfuse span level=ERROR
- [x] 4.6 实现 `after_model_request()` — 遍历 response.parts 发布 `thinking` 和 `text_stream` 事件
- [x] 4.7 实现 `after_run()` — 发布 `text_stream(is_final=True)` 流终止标记

## 5. 注册 Capabilities 到 Agent（Phase 4a + Phase 6）

- [x] 5.1 在 `src_deepagent/orchestrator/agent_factory.py` 中构建 `capabilities` 列表，按 settings 开关添加 `EventPublishingCapability`
- [x] 5.2 在 `src_deepagent/orchestrator/agent_factory.py` 中按 settings 的 `blocked_tools` 配置添加 `ToolGuard` capability
- [x] 5.3 将 `capabilities` 列表传入 `create_deep_agent(capabilities=capabilities)`
- [x] 5.4 更新 `create_hooks()` 调用，移除 `publish_fn=publish_fn` 参数

## 6. 移除 rest_api.py 内联事件推送（Phase 4b + 4c + 4e）

- [x] 6.1 在 `src_deepagent/gateway/rest_api.py` 的 `_run_agent()` 中移除 `pending_tool_calls`、`reported_tool_ids` 状态变量
- [x] 6.2 移除 `CallToolsNode` 分支中的 thinking/tool_call 内联推送（约 L413-436）
- [x] 6.3 移除 `ModelRequestNode` 分支中的 thinking/text_stream 内联推送（约 L438-459）
- [x] 6.4 移除 `End` 分支中的 thinking 提取、pending flush、fallback 推送、流终止标记（约 L461-518），保留 `break`
- [x] 6.5 移除 `_flush_pending_tool_results()` 函数（约 L260-311）
- [x] 6.6 移除 `_WRAPPED_TOOL_NAMES` 常量（约 L227-232）
- [x] 6.7 移除 `_handle_emit_chart_result()` 函数（约 L235-257）
- [x] 6.8 移除 `set_publish_fn(...)` 调用及其 import

## 7. 移除 base_tools.py ContextVar 路径（Phase 4d）

- [x] 7.1 在 `src_deepagent/capabilities/base_tools.py` 中移除 `_publish_fn_var` ContextVar 和 `set_publish_fn()` 函数
- [x] 7.2 移除 `_wrap_with_tool_result()` 包装器函数
- [x] 7.3 移除 `_infer_tool_type_local()` 函数
- [x] 7.4 更新 `create_base_tools()` 返回值，将 `_w(fn)` 替换为直接 `fn`
- [x] 7.5 移除 `emit_chart` 工具函数中的直接 publish 调用（由 Capability 处理）

## 8. 更新 security 桩文件（Phase 6）

- [x] 8.1 更新 `src_deepagent/security/permissions.py`，替换 TODO 桩为 ToolGuard 集成说明文档

## 9. 验证

- [ ] 9.1 启动服务 `python run_deepagent.py`，发送请求，验证 SSE 事件流完整性（tool_call、tool_result、thinking、text_stream、render_widget、is_final）（需手动验证）
- [ ] 9.2 验证 pydantic-deep 内置工具（write_todos 等）的 tool_result 事件正常发布（需手动验证）
- [ ] 9.3 验证 `BLOCKED_TOOLS` 配置生效，黑名单工具被拦截（需手动验证）
- [ ] 9.4 验证 `AUDIT_HOOKS_ENABLED=false` 时审计日志不输出（需手动验证）
