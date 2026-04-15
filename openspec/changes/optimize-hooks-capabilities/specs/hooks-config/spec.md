## ADDED Requirements

### Requirement: HooksSettings 配置化
系统 SHALL 在 `AppSettings` 中新增 `HooksSettings` 嵌套配置类，通过环境变量控制所有 hook 和 capability 的行为参数。

#### Scenario: 循环检测参数可配置
- **WHEN** 设置 `LOOP_WINDOW_SIZE=30`、`LOOP_WARN_THRESHOLD=5`、`LOOP_HARD_LIMIT=8`
- **THEN** 循环检测 hook MUST 使用这些值替代默认值（20/3/5）

#### Scenario: 默认值与当前行为一致
- **WHEN** 未设置任何 hooks 相关环境变量
- **THEN** 所有参数 MUST 使用与当前硬编码一致的默认值（window_size=20、warn_threshold=3、hard_limit=5、audit_enabled=true）

#### Scenario: 审计 hook 可禁用
- **WHEN** 设置 `AUDIT_HOOKS_ENABLED=false`
- **THEN** `create_hooks()` MUST 不注册审计相关的 hook

#### Scenario: 安全工具黑名单可配置
- **WHEN** 设置 `BLOCKED_TOOLS=dangerous_tool,risky_tool`
- **THEN** ToolGuard MUST 拦截名为 `dangerous_tool` 和 `risky_tool` 的工具调用

### Requirement: 审计 Hook 并发安全
系统 SHALL 修复审计 hook 的 `call_start_times` 数据结构，支持同名工具的并发调用计时。

#### Scenario: 并发调用同名工具
- **WHEN** 两个 `execute_api_call` 工具调用并发执行（调用 A 先开始，调用 B 后开始，调用 B 先完成）
- **THEN** 调用 B 的 elapsed time MUST 基于调用 B 自己的 start time 计算，不受调用 A 影响

#### Scenario: 单工具调用行为不变
- **WHEN** 只有一个工具调用在执行
- **THEN** elapsed time 计算结果 MUST 与修复前一致

#### Scenario: start time 缺失时降级
- **WHEN** `log_result` 被调用但对应的 start time 列表为空
- **THEN** elapsed MUST 显示为 "unknown"，不抛出异常

### Requirement: 移除 Token Tracker 空壳
系统 SHALL 移除 `create_token_tracker_hooks()` 函数及其在 `create_hooks()` 中的调用。Token 追踪由 `CostTracking` capability 负责。

#### Scenario: 移除后无副作用
- **WHEN** `create_hooks()` 被调用
- **THEN** 返回的 hook 列表 MUST 不包含 `AFTER_MODEL_REQUEST` 事件的 hook

#### Scenario: CostTracking 仍正常工作
- **WHEN** Agent 执行完成
- **THEN** `CostTracking` capability（通过 `cost_tracking=True` 启用）MUST 继续正常追踪 token 用量

### Requirement: 移除事件推送 Hook 死代码
系统 SHALL 移除 `create_event_push_hooks()` 函数及其在 `create_hooks()` 中的调用。事件发布由 `EventPublishingCapability` 负责。

#### Scenario: create_hooks 不再接受 publish_fn 参数
- **WHEN** `create_hooks()` 被调用
- **THEN** 函数签名 MUST 不包含 `publish_fn` 参数

#### Scenario: 移除后 hook 列表只包含循环检测和审计
- **WHEN** `create_hooks()` 被调用且 `audit_enabled=true`
- **THEN** 返回的 hook 列表 MUST 只包含 `PRE_TOOL_USE`（循环检测 + 审计）、`POST_TOOL_USE`（审计）、`POST_TOOL_USE_FAILURE`（审计）、`BEFORE_RUN`（循环检测重置）事件的 hook

### Requirement: ToolGuard 安全能力
系统 SHALL 通过 `pydantic_ai_shields.ToolGuard` 提供配置化的工具黑名单拦截能力。

#### Scenario: 黑名单工具被拦截
- **WHEN** `BLOCKED_TOOLS=dangerous_tool` 且 Agent 尝试调用 `dangerous_tool`
- **THEN** ToolGuard MUST 拦截调用，Agent 收到 `ModelRetry` 异常提示工具被阻止

#### Scenario: 黑名单为空时不注册
- **WHEN** `BLOCKED_TOOLS` 未设置或为空字符串
- **THEN** `create_orchestrator_agent` MUST 不注册 ToolGuard capability

#### Scenario: 非黑名单工具正常执行
- **WHEN** `BLOCKED_TOOLS=dangerous_tool` 且 Agent 调用 `execute_rag_search`
- **THEN** 工具 MUST 正常执行，不受 ToolGuard 影响
