## Why

当前 `run_orchestrator` 的执行链路存在三个核心问题：
1. **过度规划**：所有请求都经过同一条路径，简单的"写个快排"被拆成 5 步 DAG，导致 context 膨胀、沙箱 instruction 过长、LLM 重试时丢失参数
2. **模式路由粗暴**：虽然 `QueryRequest.mode` 支持 auto/direct/react/plan_and_execute 四种模式，但当前实现中 direct 模式跳过 Agent 用关键词匹配判断任务类型，丢失了意图理解能力；auto 模式额外调一次 LLM 分类浪费延迟
3. **工具集无差异**：所有模式下 Agent 看到完全相同的工具列表，无法通过约束工具集来引导执行路径

参考 Semantic Kernel 的 FunctionChoiceBehavior 模式（同一 Agent + 不同工具可见性）、LangGraph 的 Router 条件边模式、以及 Coze 的意图识别节点设计，重构执行链路为"意图分类 → 工具集装配 → 统一 Agent 执行"三阶段管道。

## What Changes

- **BREAKING** 移除现有的 `_classify_intent`（fast LLM 分类）、`_make_direct_fn`（关键词匹配跳过 Agent）、`_make_react_fn`、`_make_plan_execute_fn` 四个函数
- 新增 `IntentRouter`：轻量意图分类器，优先用规则匹配（零延迟），仅对模糊意图 fallback 到 fast LLM
- 新增 `ToolSetAssembler`：根据执行模式装配不同的工具子集，约束 Agent 的行为空间
- 改造 `run_orchestrator`：统一为"分类 → 装配 → 执行"三阶段管道，所有模式都经过同一个 Agent（保留意图理解能力）
- 简化执行模式为三种：`auto`（默认，Agent 自主决定）、`direct`（禁用规划工具，直接执行）、`plan_and_execute`（强制先规划再执行）
- 移除 `react` 作为独立模式（它是沙箱内 pi-mono 的执行模式，不属于 Orchestrator 层面）

## Non-goals

- 不引入 LangGraph 替换 PydanticAI
- 不改变 Worker 的执行逻辑和安全模型
- 不改变 A2UI 协议和前端渲染
- 不改变 middleware pipeline（它在执行链路外层，不受影响）
- 不引入可视化 DAG 编辑器（Coze/Dify 模式）

## Capabilities

### New Capabilities

- `intent-router`: 轻量意图分类器，规则优先 + LLM fallback，将用户请求分类为 direct/auto/plan_and_execute 模式
- `toolset-assembler`: 工具集装配器，根据执行模式动态组装 Agent 可用的工具子集

### Modified Capabilities

- `orchestrator`: 执行入口重构为三阶段管道（分类 → 装配 → 执行），移除四个模式函数，统一 Agent 执行路径

## Impact

- `src/orchestrator/orchestrator_agent.py` — 重构 `run_orchestrator` 入口，移除旧模式函数，集成 IntentRouter + ToolSetAssembler
- `src/orchestrator/intent_router.py` — 新增文件
- `src/orchestrator/toolset_assembler.py` — 新增文件
- `src/orchestrator/prompts/system.py` — 简化 system prompt，移除"简单任务直通规则"（由 IntentRouter 承担）
- `src/schemas/api.py` — `QueryRequest.mode` 移除 `react` 选项
- `src/gateway/rest_api.py` — 无变化（已透传 mode 参数）
