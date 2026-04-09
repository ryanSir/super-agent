## Context

当前 super-agent 第一阶段已完成，采用单 Agent + Workers 架构。主 Agent（PydanticAI Orchestrator）通过 11 个工具直接调用确定性 Worker（RAG/DB/API/Sandbox）。面对复杂多步骤任务，所有中间结果累积在主 Agent 上下文中，导致上下文膨胀和推理质量下降。

本次改造在 `src-deepagent/` 目录下独立开发，全栈采用 pydantic-deepagents，引入 Sub-Agent 架构和 ReasoningEngine 推理引擎。复用现有基础设施（Redis、Milvus、E2B、Langfuse），不集成 Temporal。

## Goals / Non-Goals

**Goals:**
- 基于用户问题复杂度动态选择执行模式（DIRECT / AUTO / PLAN_AND_EXECUTE / SUB_AGENT）
- Sub-Agent 拥有独立 LLM 推理、独立上下文、独立工具集，支持并行执行
- 主 Agent 和 Sub-Agent 统一技术栈（pydantic-deepagents），消除胶水代码
- 工具资源一次获取向下传递，避免 MCP 重复连接
- 企业级编码规范：type hints、结构化日志、异常层级、async 全异步

**Non-Goals:**
- Multi-Agent 双向通信
- Temporal 工作流集成
- Human-in-the-loop 审批
- 检查点与断点恢复
- 用户级别 Token 配额

## Decisions

### D1: 全栈 pydantic-deepagents vs 仅 Sub-Agent 层使用

**选择**: 全栈 deepagents

**替代方案**: 主 Agent 保持自建 PydanticAI，仅 Sub-Agent 层用 deepagents

**理由**: 统一技术栈的长期收益大于分层灵活性。分层方案会导致两套工具注册方式、两套上下文管理、两套 cost tracking 并存，胶水代码越来越多。全栈方案下 SubAgentToolset 天然支持委派（task/check_task/cancel_task），不需要自建 delegate_to_sub_agent。

### D2: Agent-as-Tool 集成模式

**选择**: Sub-Agent 对主 Agent 来说是一个工具函数

**替代方案 A**: SubAgent Worker 层（复用 WorkerProtocol）— 模糊了 Worker 和 Agent 的边界
**替代方案 B**: 独立编排层 — 过度设计，增加不必要的抽象层

**理由**: Agent-as-Tool 与 PydanticAI 的 @agent.tool 机制天然兼容，改动最小。主 Agent 完全控制委派时机和结果汇总。Sub-Agent 的 SubAgentInput → SubAgentOutput 契约自包含，未来升级 multi-agent 只需加消息总线，Sub-Agent 本身不需要改。

### D3: ReasoningEngine 合并三组件

**选择**: 将 IntentRouter + ComplexityEvaluator + ToolSetAssembler 合并为 ReasoningEngine

**替代方案**: 保持三个独立组件

**理由**: 加了复杂度评估后，意图理解 → 复杂度评估 → 模式决策 → 工具装配是一个完整的决策链，拆成三个组件会导致状态在组件间传递。合并后三阶段流水线简化为两阶段（Reason → Execute），ReasoningEngine.decide() 一次性输出 ExecutionPlan。

### D4: 工具资源一次获取

**选择**: ReasoningEngine.decide() 阶段统一获取 Workers/MCP/Skills/桥接工具，通过 ResolvedResources 向下传递

**替代方案**: 每个 Agent/Sub-Agent 各自获取所需资源

**理由**: MCP 连接是网络操作，每次握手有延迟。三个 Sub-Agent 并行时如果各自连接，就是三次额外网络开销。一次获取后通过桥接工具共享，整个请求生命周期内 MCP 连接只建立一次。

### D5: 复杂度评估策略

**选择**: 五维度规则加权 + 模糊区间 LLM 兜底

**维度**: task_count(0.25) + domain_span(0.20) + dependency_depth(0.20) + output_complexity(0.15) + reasoning_depth(0.20)

**替代方案 A**: 纯 LLM 分类 — 每次请求多一次 LLM 调用，增加延迟和成本
**替代方案 B**: 纯规则 — 边界 case 不够准确

**理由**: 规则层零延迟处理大部分明确 case，只在评分 0.35~0.55 模糊区间调用轻量 LLM（fast_model）做二次判断，平衡准确性和性能。

### D6: Hooks 替代中间件管道

**选择**: 用 deepagents 的 Hooks 机制替代自建的洋葱模型中间件

**替代方案**: 保留自建中间件管道

**理由**: deepagents 的 Hooks 是其原生扩展点，与 history_processors、capabilities 等机制协同工作。自建中间件管道与 deepagents 的内部机制会冲突。循环检测、事件推送、审计日志都可以通过 Hook 实现。

### D7: 保留自建 Redis Memory

**选择**: 不使用 deepagents 的 MemoryToolset，保留自建 Redis Memory

**替代方案**: 使用 deepagents 内置的 MEMORY.md 文件持久化

**理由**: deepagents 的 MemoryToolset 基于文件系统（MEMORY.md），不适合多用户并发场景。自建方案基于 Redis Hash + Sorted Set，支持分布式锁、200ms 超时降级、LLM 自动抽取，更适合企业级多用户环境。

### D8: 三个预置 Sub-Agent 角色

**选择**: Research + Analysis + Writing，代码执行继续走 SandboxWorker → Pi Agent

**替代方案**: 加 Coding Sub-Agent

**理由**: Pi Agent 本身已经是沙箱内的通用 ReAct Agent，具备完整的代码生成和执行能力。加 Coding Sub-Agent 会导致两层 LLM 推理叠加（Coding Sub-Agent → Pi Agent），中间层成为多余的传话层。

## Risks / Trade-offs

**[R1: deepagents 框架成熟度]** → 框架较新，可能有 bug 或能力缺口。缓解：底层是 PydanticAI，团队已熟悉；子包独立发布，可按需替换单个子包。

**[R2: 复杂度评估准确性]** → 规则层可能误判边界 case。缓解：LLM 兜底层覆盖模糊区间；用户可通过 mode 参数显式指定执行模式。

**[R3: Sub-Agent token 成本]** → 复杂任务下每个 Sub-Agent 独立消耗 token，总成本增加。缓解：deepagents 内置 cost tracking 精确追踪；SummarizationProcessor 控制上下文膨胀；简单任务不触发 Sub-Agent。

**[R4: 桥接工具适配]** → Workers 的 TaskNode 接口与 deepagents 工具函数签名不同，需要桥接层。缓解：桥接层是薄封装（每个工具约 10 行），持有 Worker 实例引用，无额外网络开销。

**[R5: Hooks 能力边界]** → deepagents Hooks 可能不完全覆盖原中间件管道的所有功能（如 on_tool_call 拦截）。缓解：需要验证 Hooks API 的事件类型覆盖度，必要时通过 capabilities 扩展。

## Migration Plan

1. `src-deepagent/` 独立开发，不影响 `src/` 现有服务
2. 新旧服务可并行运行在不同端口
3. 验证通过后，网关层切换路由到新服务
4. 无需数据迁移（共用 Redis/Milvus/E2B）
5. 回滚策略：切回 `src/` 服务即可

## Open Questions

- deepagents SubAgentToolset 的 `task()` 是否支持传递 parent_results（前置任务结果注入）？需要验证 API
- deepagents Hooks 的事件类型列表是否覆盖 tool_call_start / tool_call_end？需要查看源码确认
- 桥接工具的 ctx 参数类型是否与 deepagents 的 RunContext 兼容？需要实际测试
