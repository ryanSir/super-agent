## ADDED Requirements

### Requirement: Agent Factory 三阶段构建
系统 SHALL 实现 Agent Factory 的三阶段构建流程：Resolve（解析意图+获取资源）→ Assemble（组装上下文+工具+配置）→ Create（创建 Agent 实例）。每个阶段 SHALL 独立可测试，阶段间通过明确的数据结构传递。

#### Scenario: 正常三阶段构建
- **WHEN** 收到用户查询请求，ReasoningEngine 返回 ExecutionPlan
- **THEN** Agent Factory 依次执行 Resolve → Assemble → Create，返回可执行的 Agent 实例和 Deps 对象

#### Scenario: Resolve 阶段资源获取失败
- **WHEN** Resolve 阶段获取 MCP 工具或 Skill 资源失败
- **THEN** 系统 SHALL 降级为可用资源子集继续构建，并在日志中记录降级原因

#### Scenario: 构建超时
- **WHEN** 三阶段构建总耗时超过 10 秒
- **THEN** 系统 SHALL 中断构建并返回超时错误，释放已获取的资源

### Requirement: 13-Stage Middleware Pipeline
系统 SHALL 实现 13 阶段中间件管道，按顺序执行：1.RequestValidation → 2.RateLimiting → 3.Authentication → 4.PermissionCheck → 5.ContextEnrichment → 6.MemoryRetrieval → 7.IntentClassification → 8.ModeRouting → 9.ToolResolution → 10.Execution → 11.OutputValidation → 12.CostTracking → 13.AuditLogging。每个 stage SHALL 可独立启用/禁用。

#### Scenario: 完整管道执行
- **WHEN** 请求通过所有 13 个 stage
- **THEN** 每个 stage 的执行时间 SHALL 被记录，总延迟 SHALL 在 Prometheus 指标中上报

#### Scenario: 中间件短路
- **WHEN** PermissionCheck stage 拒绝请求
- **THEN** 管道 SHALL 立即终止，跳过后续 stage，返回 403 错误

#### Scenario: 单个 stage 异常
- **WHEN** 某个非关键 stage（如 MemoryRetrieval）抛出异常
- **THEN** 系统 SHALL 跳过该 stage 继续执行，并记录告警日志

### Requirement: Context Manager 动态上下文组装
系统 SHALL 实现 Context Manager，从模板文件动态组装 System Prompt。组装内容包括：角色定义、运行时上下文、思考策略、澄清系统、执行模式指令、工具使用规范、Skill 摘要、SubAgent 指令、MCP 工具列表、用户记忆、回复风格、关键提醒。

#### Scenario: 按执行模式组装
- **WHEN** ReasoningEngine 决策为 AUTO 模式
- **THEN** Context Manager SHALL 加载 mode_auto.md 模板，注入 SubAgent 段落，包含全量工具可见性

#### Scenario: DIRECT 模式精简组装
- **WHEN** 执行模式为 DIRECT
- **THEN** Context Manager SHALL 不注入 SubAgent 段落，隐藏 plan_and_decompose 工具

#### Scenario: 模板文件缺失
- **WHEN** 某个模板文件不存在或读取失败
- **THEN** 系统 SHALL 使用内置默认文本替代，并记录 WARNING 日志

### Requirement: ask_clarification 澄清机制
系统 SHALL 实现三阶段澄清机制：CLARIFY（识别模糊意图）→ PLAN（生成澄清问题）→ ACT（等待用户回复后继续执行）。澄清问题 SHALL 通过 SSE 事件推送到前端。

#### Scenario: 触发澄清
- **WHEN** Agent 判断用户意图模糊（缺少关键参数或存在歧义）
- **THEN** 系统 SHALL 暂停执行，推送 clarification_needed 事件，包含结构化问题列表

#### Scenario: 用户回复澄清
- **WHEN** 用户回复澄清问题
- **THEN** 系统 SHALL 将回复注入上下文，从暂停点继续执行，不重新开始

#### Scenario: 澄清超时
- **WHEN** 用户 5 分钟内未回复澄清问题
- **THEN** 系统 SHALL 基于最佳猜测继续执行，并在输出中标注假设

### Requirement: 四种执行模式完整生命周期
系统 SHALL 支持 DIRECT / AUTO / PLAN_AND_EXECUTE / SUB_AGENT 四种执行模式，每种模式 SHALL 有完整的启动、执行、监控、完成/失败生命周期。模式选择由 ReasoningEngine 的五维度复杂度评估决定。

#### Scenario: DIRECT 模式执行
- **WHEN** 复杂度评估为 LOW（score < 0.35）
- **THEN** 系统 SHALL 使用 DIRECT 模式，Agent 直接回答不调工具，响应时间 SHALL < 3 秒

#### Scenario: AUTO 模式执行
- **WHEN** 复杂度评估为 MEDIUM（0.35 ≤ score < 0.55）
- **THEN** 系统 SHALL 使用 AUTO 模式，Agent 自主决定工具调用组合

#### Scenario: PLAN_AND_EXECUTE 模式执行
- **WHEN** 复杂度评估为 MEDIUM 且规则匹配到多步骤模式
- **THEN** 系统 SHALL 使用 PLAN_AND_EXECUTE 模式，先生成 DAG 再按顺序执行

#### Scenario: SUB_AGENT 模式执行
- **WHEN** 复杂度评估为 HIGH（score ≥ 0.55）
- **THEN** 系统 SHALL 使用 SUB_AGENT 模式，通过 task() 委派子 Agent 执行

#### Scenario: DIRECT → AUTO 模式升级
- **WHEN** DIRECT 模式执行后输出为空或 Agent 自述无法完成
- **THEN** 系统 SHALL 自动升级到 AUTO 模式重试（最多一次），推送 mode_escalated 事件

### Requirement: 五维度复杂度评估
系统 SHALL 实现五维度加权复杂度评估：task_count（任务数量）、domain_span（领域跨度）、dependency_depth（依赖深度）、output_complexity（输出复杂度）、reasoning_depth（推理深度）。评估结果为 0-1 的分数。

#### Scenario: 规则评估明确
- **WHEN** 五维度加权分数 < 0.35 或 ≥ 0.55
- **THEN** 系统 SHALL 直接使用规则分数，不调用 LLM

#### Scenario: 模糊区间 LLM 兜底
- **WHEN** 分数落在 [0.35, 0.55] 模糊区间
- **THEN** 系统 SHALL 调用 fast_model 进行二次判断，超时 5 秒降级为规则分数