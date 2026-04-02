## Context

当前 `run_orchestrator` 存在四个独立的执行路径函数（`_make_direct_fn`、`_make_react_fn`、`_make_plan_execute_fn`、`_classify_intent`），导致：

1. direct 模式用关键词匹配跳过 Agent，丢失意图理解能力
2. auto 模式每次额外调一次 fast LLM 做分类，增加 ~500ms 延迟
3. react 和 plan_and_execute 调同一个 Agent 但无工具集差异，区分度不够
4. 四个函数各自维护 MCP fallback、token usage 更新、历史保存等重复逻辑

参考业界主流框架的设计：
- **Semantic Kernel**：同一 Agent + `FunctionChoiceBehavior`（Auto/Required/None）控制工具可见性
- **LangGraph**：Router 节点 + conditional edges 分流到不同子图
- **Coze**：意图识别节点（规则优先）+ 条件分支
- **OpenAI Swarm**：函数返回值决定路由，无额外分类调用

核心洞察：**不需要多条执行路径，只需要一个 Agent + 不同的工具集约束**。

## Goals / Non-Goals

**Goals:**

- 统一为单一 Agent 执行路径，通过工具集约束区分模式
- IntentRouter 规则优先（零延迟），仅模糊意图 fallback LLM
- 消除重复的 MCP fallback / token usage / 历史保存逻辑
- 保持与 middleware pipeline 的兼容性

**Non-Goals:**

- 不引入 LangGraph 状态图
- 不改变 Worker 执行逻辑
- 不改变 middleware pipeline
- 不引入可视化工作流编辑器

## Decisions

### Decision 1: 三阶段管道架构（Classify → Assemble → Execute）

**选择**: 将执行链路重构为三个解耦的阶段

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ IntentRouter │───▶│ ToolSetAssembler │───▶│ Agent Execution │
│ (分类模式)    │    │ (装配工具集)      │    │ (统一执行)       │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

**理由**: 参考 Semantic Kernel 的设计哲学 — 不需要多个 Agent 或多条路径，只需要控制同一个 Agent 看到的工具集。三阶段解耦让每个阶段可以独立测试和替换。

**替代方案**:
- 多 Agent 方案（CrewAI 模式）→ 维护成本高，PydanticAI 不原生支持 Agent 间通信
- 单一 Agent 无约束（当前 react 模式）→ Agent 倾向于过度规划

### Decision 2: IntentRouter 规则优先 + LLM fallback

**选择**: 两级分类策略

```python
class IntentRouter:
    def classify(self, query: str, mode: str) -> ExecutionMode:
        # Level 0: 用户显式指定 mode
        if mode != "auto":
            return ExecutionMode(mode)

        # Level 1: 规则匹配（零延迟）
        if self._match_direct_patterns(query):
            return ExecutionMode.DIRECT
        if self._match_plan_patterns(query):
            return ExecutionMode.PLAN_AND_EXECUTE

        # Level 2: 默认 auto（Agent 自主决定）
        return ExecutionMode.AUTO
```

**理由**: 参考 Coze 的意图识别节点 — 规则匹配覆盖 80% 的明确意图（"写个快排" → direct，"检索+分析+可视化" → plan），剩余 20% 模糊意图让 Agent 自己判断（auto）。完全避免了额外 LLM 调用。

**规则匹配策略**:
- `direct` 模式触发词：单一动作动词 + 明确对象（"写/实现/编写 + 代码/算法/脚本"、"搜索/检索 + 论文/专利"）
- `plan_and_execute` 模式触发词：多步骤连接词（"并且/然后/接着"、"先...再...最后"、"对比...分析...生成"）
- 其余 → `auto`（Agent 自主决定是否调用 plan_and_decompose）

**替代方案**:
- 纯 LLM 分类（当前方案）→ 每次多 500ms + 额外 token 成本
- 纯规则匹配 → 无法处理模糊意图
- 嵌入向量相似度 → 过度工程化

### Decision 3: ToolSetAssembler 按模式装配工具子集

**选择**: 三种工具集配置

| 模式 | 可用工具 | 禁用工具 | 行为效果 |
|------|---------|---------|---------|
| `direct` | execute_sandbox_task, execute_native_worker, execute_skill, search_skills, emit_chart, emit_widget, recall_memory | plan_and_decompose, list_available_skills, create_new_skill | Agent 直接选择执行工具，不会规划 |
| `auto` | 全部工具 | 无 | Agent 自主决定是否规划（Semantic Kernel Auto 模式） |
| `plan_and_execute` | 全部工具 | 无，但 system prompt 强制先规划 | Agent 必须先调 plan_and_decompose |

**理由**: 参考 Semantic Kernel 的 `FunctionChoiceBehavior` — direct 模式通过移除 `plan_and_decompose` 工具，从根本上阻止 Agent 进行规划。这比在 prompt 中说"不要规划"更可靠，因为 LLM 可能忽略 prompt 指令，但无法调用不存在的工具。

**实现方式**: PydanticAI 支持在 `agent.run()` 时动态传入 `toolsets` 参数。ToolSetAssembler 返回一个过滤后的工具列表，而非修改 Agent 定义。

**替代方案**:
- 创建多个 Agent 实例（每个模式一个）→ 内存浪费，工具定义重复
- 仅靠 prompt 引导 → 不可靠，LLM 可能忽略

### Decision 4: 统一执行函数消除重复逻辑

**选择**: 单一 `_execute_agent` 函数处理所有模式

```python
async def _execute_agent(
    ctx: MiddlewareContext,
    query: str,
    deps: OrchestratorDeps,
    tool_filter: Optional[Callable] = None,
    prompt_prefix: str = "",
) -> OrchestratorOutput:
    """统一 Agent 执行函数"""
    effective_query = prompt_prefix + query
    toolsets = _get_mcp_toolsets()

    # 应用工具过滤
    if tool_filter:
        # PydanticAI 工具过滤逻辑
        ...

    # MCP fallback
    try:
        result = await orchestrator_agent.run(...)
    except ...:
        result = await orchestrator_agent.run(...)  # 无 MCP

    # 统一的 token usage 更新、历史保存、A2UI 帧注入
    ...
    return output
```

**理由**: 当前四个 `_make_*_fn` 函数中 80% 的代码是重复的（MCP fallback、token usage、历史保存）。统一后只需维护一份逻辑。

## Risks / Trade-offs

**[Risk] 规则匹配误分类** → 规则仅覆盖高置信度的明确意图，模糊意图走 auto 让 Agent 自己判断。误分类的最坏情况是 direct 模式下 Agent 发现需要规划但没有 plan_and_decompose 工具，此时 Agent 会直接用可用工具完成任务（这正是我们想要的行为）

**[Risk] PydanticAI 工具过滤能力限制** → PydanticAI 的 `agent.run()` 不直接支持运行时工具过滤。需要通过创建 Agent 的浅拷贝或使用 `toolsets` 参数实现。如果 PydanticAI 不支持，fallback 方案是为每个模式维护独立的 Agent 实例（lazy 初始化）

**[Trade-off] 移除 react 模式** → react 本来是沙箱内 pi-mono 的执行模式（Thought→Action→Observation），不属于 Orchestrator 层面。移除后 `QueryRequest.mode` 的 pattern 需要更新，这是一个 **BREAKING** 变更

## Migration Plan

1. 新增 `intent_router.py` 和 `toolset_assembler.py`（无破坏性）
2. 重构 `run_orchestrator`，替换四个模式函数为三阶段管道
3. 更新 `QueryRequest.mode` pattern，移除 `react`
4. 简化 system prompt，移除"简单任务直通规则"
5. 清理旧代码（`_classify_intent`、`_make_*_fn`）

**回滚策略**: 如果新链路出现问题，可以通过配置开关回退到旧的 react 模式（保留旧代码但标记 deprecated，通过环境变量 `USE_LEGACY_PIPELINE=true` 切换）

## Open Questions

- PydanticAI 是否支持运行时动态过滤 Agent 的工具列表？需要验证 API。如果不支持，备选方案是为 direct 模式创建一个独立的 Agent 实例（共享 model 和 instructions，但工具列表不同）
