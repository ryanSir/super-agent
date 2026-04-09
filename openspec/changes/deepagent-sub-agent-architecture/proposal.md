## Why

当前 super-agent 是单 Agent + Workers 架构，主 Agent（PydanticAI Orchestrator）直接调用确定性 Worker 执行任务。面对复杂的多步骤任务（如"搜索论文→分析趋势→生成报告"），所有工具调用的中间结果都累积在主 Agent 上下文中，导致上下文膨胀、推理质量下降、无法并行执行。

需要引入 Sub-Agent 架构：基于用户问题复杂度动态选择执行模式，复杂任务委派给有独立 LLM 推理能力的 Sub-Agent，每个 Sub-Agent 拥有独立上下文和工具集，支持并行执行。全栈采用 pydantic-deepagents 统一技术栈，在 `src-deepagent/` 目录下独立开发。

## Non-goals

- 不实现 Multi-Agent 协作（Agent 间双向通信），当前只做单向委派的 Sub-Agent 模式
- 不集成 Temporal 工作流引擎，采用直接异步执行
- 不迁移或修改 `src/` 目录下的老代码
- 不实现 Human-in-the-loop 审批机制（后续迭代）
- 不实现检查点与断点恢复（后续迭代）
- 不实现用户级别的 Token 配额和速率限制（后续迭代）

## What Changes

- 新增 `src-deepagent/` 独立代码目录，全栈基于 pydantic-deepagents 重新开发
- 新增 ReasoningEngine（推理引擎），合并意图理解 + 复杂度评估 + 执行模式决策 + 工具资源获取为统一的两阶段流水线（Reason → Execute）
- 新增 ExecutionMode.SUB_AGENT 执行模式，复杂任务自动路由到 Sub-Agent 编排
- 新增三个预置 Sub-Agent 角色：Research（信息检索）、Analysis（数据分析）、Writing（报告撰写）
- 主 Agent 改用 `create_deep_agent()` 创建，获得 SubAgentToolset（内置委派）、TodoToolset（任务规划）、SummarizationProcessor（上下文压缩）、Cost tracking（成本追踪）
- 新增 Worker 桥接层，将现有 Workers/Skills 包装为 deepagents 兼容的工具函数，主 Agent 和 Sub-Agent 共享
- 新增 Hooks 机制替代中间件管道，实现事件推送、循环检测、安全审计
- 工具资源（Workers/MCP/Skills）一次获取向下传递，避免 MCP 重复连接
- **BREAKING**: 新代码在 `src-deepagent/` 独立运行，不兼容 `src/` 的 API 接口（后续统一）

## Capabilities

### New Capabilities

- `reasoning-engine`: 推理引擎，合并意图理解、复杂度评估（五维度规则+LLM兜底）、执行模式决策、工具资源一次性获取，输出 ExecutionPlan
- `sub-agent-orchestration`: Sub-Agent 编排能力，包括 Agent-as-Tool 集成模式、三个预置角色（Research/Analysis/Writing）、声明式 SubAgentConfig、桥接工具层
- `agent-runtime`: 基于 pydantic-deepagents 的 Agent 运行时，包括主 Agent 工厂、Hooks 体系（事件推送/循环检测/审计）、deepagents 能力集成（TodoToolset/SummarizationProcessor/CostTracking）

### Modified Capabilities

- `orchestrator`: 执行模式新增 SUB_AGENT，OrchestratorOutput 新增 sub_agent_results 字段，流水线从三阶段改为两阶段
- `workers`: Worker 层通过桥接工具暴露给 deepagents Agent 和 Sub-Agent，WorkerProtocol 不变
- `streaming`: SSE 事件类型扩展，新增 sub_agent_started/sub_agent_completed 等 Sub-Agent 生命周期事件

## Impact

- 依赖：新增 `pydantic-deep[cli]` 及其子包（`pydantic-ai-backend`、`pydantic-ai-todo`、`subagents-pydantic-ai`、`summarization-pydantic-ai`）
- 代码：`src-deepagent/` 全新目录，约 25 个文件，不影响 `src/`
- API：新的 REST/WebSocket 端点（独立于 `src/` 的网关）
- 基础设施：复用现有 Redis、Milvus、E2B、Langfuse，无新增基础设施
- LLM 成本：Sub-Agent 模式下每个 Sub-Agent 独立消耗 token，复杂任务总 token 用量会增加，但主 Agent 上下文更干净、推理质量更高