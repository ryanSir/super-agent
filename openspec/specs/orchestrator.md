# Orchestrator 规格

## 职责

系统的"Python 大脑"，基于 PydanticAI 实现 Orchestrator-Workers 编排模式。
负责意图理解、DAG 规划、任务路由分发、结果整合，以及 A2UI 事件推送。

## 核心文件

- `src/orchestrator/orchestrator_agent.py` — Agent 定义 + Tool 实现 + 编排入口
- `src/orchestrator/planner.py` — DAG 规划器（LLM 生成任务拓扑）
- `src/orchestrator/router.py` — 任务路由（风险等级 → Worker 映射）
- `src/orchestrator/prompts/system.py` — 系统 Prompt
- `src/orchestrator/prompts/planning.py` — DAG 规划 Prompt 模板

## 依赖注入

```python
@dataclass
class OrchestratorDeps:
    session_id: str       # 会话 ID
    trace_id: str         # 分布式追踪 ID
    workers: Dict[str, Any]     # 已注册 Worker 实例
    context: Dict[str, Any]     # 附加上下文
    a2ui_frames: List[Dict]     # 收集的 A2UI 渲染帧
```

## 已注册 Tools

Orchestrator MUST 注册以下工具：

| Tool | 用途 |
|------|------|
| `plan_and_decompose(query)` | 将用户请求拆解为 ExecutionDAG |
| `execute_native_worker(task_id, task_type, description, input_data)` | 执行可信 Worker（RAG/DB/API） |
| `execute_sandbox_task(task_id, instruction, context_files)` | 执行 E2B 沙箱高危任务 |
| `execute_skill(skill_name, args)` | 调用已注册 Skill 脚本 |
| `search_skills(query)` | 按关键词检索匹配的 Skill，返回完整定义 |
| `list_available_skills()` | 列出所有可用 Skill 名称和摘要 |
| `create_new_skill(name, description, ...)` | 动态创建新 Skill |
| `recall_memory(user_id)` | 检索用户历史记忆 |
| `emit_chart(title, chart_type, x_axis, series_data)` | 渲染 ECharts 图表到前端 |
| `emit_widget(ui_component, props)` | 渲染任意前端组件 |

#### Scenario: Agent 调用 search_skills
- **WHEN** Agent 判断需要使用某个 Skill 但 system prompt 中仅有摘要
- **THEN** Agent 调用 `search_skills("ppt")` 获取匹配 Skill 的完整定义，注入后续上下文

#### Scenario: Agent 调用 recall_memory
- **WHEN** Agent 需要了解用户背景信息
- **THEN** Agent 调用 `recall_memory(user_id)` 获取用户画像和相关事实

## Worker 名称映射

```python
WORKER_NAME_MAP = {
    "rag_retrieval": "rag_worker",
    "db_query":      "db_query_worker",
    "api_call":      "api_call_worker",
}
# 沙箱 Worker 固定 key: "sandbox_worker"
```

## 关键约束

- 模型使用 `get_model("planning")`，retries=3
- 会话对话历史存储在内存 `_session_histories: Dict[str, list]`，按 session_id 索引
- MCP 工具集按需加载，失败自动降级为无 MCP 模式
- `answer` 为空时触发 fallback：用 `get_model("fast")` 汇总 tool 返回内容
- 所有 Tool 执行前后推送 `step` 事件，执行结果推送 `tool_result` 事件
- A2UI 渲染帧收集在 `deps.a2ui_frames`，编排完成后注入 `OrchestratorOutput.a2ui_frames`

## 编排入口

系统的"Python 大脑"，基于 PydanticAI 实现 Orchestrator-Workers 编排模式。负责意图理解、DAG 规划、任务路由分发、结果整合，以及 A2UI 事件推送。

`run_orchestrator()` 入口 MUST 实现三阶段管道：

1. **Classify**: 调用 `IntentRouter.classify(query, mode)` 获取 `ExecutionMode`
2. **Assemble**: 调用 `ToolSetAssembler.assemble(execution_mode)` 获取工具配置
3. **Execute**: 使用统一的 `_execute_agent()` 函数执行，传入工具配置

当 `middleware.enabled=true` 时，三阶段管道 MUST 被 `MiddlewarePipeline` 包裹。

`run_orchestrator()` MUST 接受 `mode` 参数（默认 "auto"），支持 "auto"、"direct"、"plan_and_execute" 三种值。

#### Scenario: auto 模式完整流程
- **WHEN** 用户发送 query="帮我分析这个数据"，mode="auto"
- **THEN** IntentRouter 返回 AUTO → ToolSetAssembler 返回全部工具 → Agent 自主决定是否规划

#### Scenario: direct 模式跳过规划
- **WHEN** 用户发送 query="写个快排"，mode="auto"，IntentRouter 分类为 DIRECT
- **THEN** ToolSetAssembler 过滤掉 plan_and_decompose → Agent 直接选择 execute_sandbox_task 执行

#### Scenario: plan_and_execute 模式强制规划
- **WHEN** 用户发送 query="检索专利并分析趋势"，mode="auto"，IntentRouter 分类为 PLAN_AND_EXECUTE
- **THEN** ToolSetAssembler 返回全部工具 + prompt_prefix → Agent 先调 plan_and_decompose 再执行

#### Scenario: middleware pipeline 包裹
- **WHEN** middleware.enabled=true
- **THEN** 三阶段管道在 MiddlewarePipeline 的 before_agent 和 after_agent 之间执行

#### Scenario: middleware pipeline 禁用
- **WHEN** middleware.enabled=false
- **THEN** 三阶段管道直接执行，不经过任何 middleware

#### Scenario: _run_orchestration 被 Temporal Activity 调用
- **WHEN** Temporal `run_orchestration` activity 调用 `_run_orchestration(session_id, trace_id, request)`
- **THEN** 函数 MUST 正常执行完整编排流程，通过 `publish_event()` 推送所有事件到 Redis Streams

### Requirement: 统一 Agent 执行函数
系统 SHALL 提供 `_execute_agent()` 内部函数，作为所有模式的统一执行入口。该函数 MUST 处理：
- MCP toolsets 加载和 fallback
- 工具过滤（根据 AssembleResult.tool_filter）
- prompt_prefix 注入
- token usage 更新到 MiddlewareContext
- A2UI 帧注入到 OrchestratorOutput
- 会话历史保存

#### Scenario: MCP 连接失败降级
- **WHEN** MCP toolsets 加载成功但执行时连接失败
- **THEN** 自动降级为无 MCP 模式重新执行

#### Scenario: 工具过滤生效
- **WHEN** AssembleResult.tool_filter = ["plan_and_decompose"]
- **THEN** Agent 执行时 plan_and_decompose 工具不可用

#### Scenario: Agent 执行超时
- **WHEN** Agent 执行超过 asyncio 超时限制
- **THEN** 抛出 OrchestrationTimeout 异常

### Requirement: 沙箱任务重试保护
`execute_sandbox_task` 工具 MUST 对同一 task_id 限制最多 2 次执行。超过后 MUST 返回失败结果并引导 Agent 用已有信息回答用户。

#### Scenario: 沙箱重试超限
- **WHEN** 同一 task_id 的沙箱任务已执行 2 次仍失败
- **THEN** 返回 `WorkerResult(success=False, error="沙箱任务已重试 2 次仍失败，请直接用已有信息回答用户")`

## 异常

- `OrchestrationTimeout` — asyncio.TimeoutError 时抛出
- `RoutingError` — 路由失败时抛出（在 router.py 中）

## 编排流程日志

### Requirement: Orchestrator 编排流程日志
Orchestrator 的 `run_orchestrator()` 函数 SHALL 在以下关键步骤使用 `pipeline_step` 记录标准化事件：
1. 意图分类（`intent.classify`）
2. 工具集装配（`toolset.assemble`）
3. 任务规划（`orchestrator.plan`）
4. Agent 执行（`orchestrator.execute`）

#### Scenario: 编排全流程事件记录
- **WHEN** `run_orchestrator()` 被调用并成功完成
- **THEN** 系统 MUST 记录至少 4 对 started/completed 事件，覆盖 intent.classify、toolset.assemble、orchestrator.plan、orchestrator.execute

#### Scenario: 规划阶段失败
- **WHEN** `plan_and_decompose()` 执行过程中抛出异常
- **THEN** 系统 MUST 记录 `orchestrator.plan` 的 failed 事件，metadata 包含错误信息，且不影响错误的正常传播

#### Scenario: 规划结果记录
- **WHEN** `plan_and_decompose()` 成功完成
- **THEN** completed 事件的 metadata MUST 包含 `task_count`（规划的任务数量）

### Requirement: Orchestrator Tool 调用日志
Orchestrator 的每个 tool 函数（execute_native_worker, execute_sandbox_task, execute_skill）SHALL 使用 `pipeline_step` 记录执行事件。

#### Scenario: Native Worker 调用事件
- **WHEN** `execute_native_worker()` 被调用
- **THEN** 系统 MUST 记录 `worker.native.{type}` 事件，metadata 包含 `worker_type` 和 `task_id`

#### Scenario: Sandbox 任务事件
- **WHEN** `execute_sandbox_task()` 被调用
- **THEN** 系统 MUST 记录 `worker.sandbox` 事件，metadata 包含 `task_id`

#### Scenario: Skill 执行事件
- **WHEN** `execute_skill()` 被调用
- **THEN** 系统 MUST 记录 `skill.execute.{name}` 事件，metadata 包含 `skill_name`
