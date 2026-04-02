## MODIFIED Requirements

### Requirement: Orchestrator 编排入口
系统的"Python 大脑"，基于 PydanticAI 实现 Orchestrator-Workers 编排模式。负责意图理解、DAG 规划、任务路由分发、结果整合，以及 A2UI 事件推送。

`run_orchestrator()` 入口 MUST 在执行 Agent 前后经过 `MiddlewarePipeline` 处理。当 `middleware.enabled=true` 时，请求流程为：MiddlewarePipeline.execute() → before_agent hooks → agent execution → after_agent hooks。当 `middleware.enabled=false` 时，直接执行 agent。

编排入口 MUST 在调用 Agent 前通过 `MemoryRetriever` 检索用户记忆，将记忆文本追加到 system prompt 的 `[User Context]` 段落。

#### Scenario: middleware 启用时的执行流程
- **WHEN** 配置 `middleware.enabled=true`，用户发起请求
- **THEN** 请求经过 MiddlewarePipeline 的 before_agent → agent 执行 → after_agent 逆序处理

#### Scenario: middleware 禁用时的执行流程
- **WHEN** 配置 `middleware.enabled=false`，用户发起请求
- **THEN** 请求直接调用 agent 函数，不经过任何 middleware

#### Scenario: 记忆注入 system prompt
- **WHEN** 用户存在历史记忆，发起新请求
- **THEN** Orchestrator 在 system prompt 中追加 `[User Context]` 段落，包含用户画像摘要

#### Scenario: 无记忆时不注入
- **WHEN** 新用户无历史记忆
- **THEN** system prompt 中不包含 `[User Context]` 段落

### Requirement: 已注册 Tools
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
