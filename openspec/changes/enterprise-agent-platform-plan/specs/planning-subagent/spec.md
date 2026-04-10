## ADDED Requirements

### Requirement: DAG 任务分解引擎
系统 SHALL 实现任务分解引擎，将复杂查询分解为 DAG（有向无环图）结构的子任务。每个 TaskNode SHALL 包含 task_id、task_type、input_data、depends_on 字段。同层无依赖的任务 SHALL 支持并行执行。

#### Scenario: 串行任务分解
- **WHEN** 用户请求 "搜索论文，分析趋势，生成图表"
- **THEN** 系统 SHALL 生成 3 个 TaskNode：t1(搜索) → t2(分析, depends_on=[t1]) → t3(图表, depends_on=[t2])

#### Scenario: 并行任务分解
- **WHEN** 用户请求 "对比分析三个竞品"
- **THEN** 系统 SHALL 生成并行节点：t1(竞品A) / t2(竞品B) / t3(竞品C) → t4(对比, depends_on=[t1,t2,t3])

#### Scenario: 循环依赖检测
- **WHEN** 分解结果中出现循环依赖
- **THEN** 系统 SHALL 拒绝该 DAG 并返回错误，不执行任何任务

### Requirement: SubAgent Executor 并发执行
系统 SHALL 实现 SubAgent Executor，支持最多 MAX_CONCURRENT_SUBAGENTS（默认 3）个 Sub-Agent 并发执行。每个 Sub-Agent SHALL 拥有独立上下文（clone_for_subagent），禁止嵌套调用。

#### Scenario: 并发执行
- **WHEN** 主 Agent 通过 task() 同时委派 3 个 Sub-Agent
- **THEN** 3 个 Sub-Agent SHALL 并行执行，各自独立上下文互不干扰

#### Scenario: 超过并发限制
- **WHEN** 主 Agent 尝试委派第 4 个 Sub-Agent（已有 3 个在运行）
- **THEN** 第 4 个 SHALL 排队等待，直到有 Sub-Agent 完成释放槽位

#### Scenario: Sub-Agent 嵌套调用
- **WHEN** Sub-Agent 内部尝试调用 task() 委派另一个 Sub-Agent
- **THEN** 系统 SHALL 拒绝该调用并返回错误 "Sub-Agent 禁止嵌套"

#### Scenario: Sub-Agent 执行超时
- **WHEN** 某个 Sub-Agent 执行超过 120 秒
- **THEN** 系统 SHALL 强制终止该 Sub-Agent，返回超时错误，主 Agent 继续处理其他结果

### Requirement: Agent Team 协调
系统 SHALL 支持预置角色（researcher / analyst / writer）和自定义 Agent 注册。预置角色 SHALL 有独立的 System Prompt 和工具权限范围。自定义 Agent 通过 AGENT.md 文件注册。

#### Scenario: 预置角色调用
- **WHEN** 主 Agent 调用 task("researcher", "调研竞品A")
- **THEN** 系统 SHALL 创建 researcher 角色的 Sub-Agent，仅可使用 rag_search/api_call/skill/search_skills/sandbox 工具

#### Scenario: 自定义 Agent 注册
- **WHEN** agents/ 目录下存在 my-agent/AGENT.md 文件
- **THEN** 系统启动时 SHALL 自动扫描并注册该 Agent，使其可通过 task("my-agent", ...) 调用

#### Scenario: 角色不存在
- **WHEN** 主 Agent 调用 task("unknown-role", ...)
- **THEN** 系统 SHALL 返回错误 "角色 unknown-role 未注册"，不创建 Sub-Agent

### Requirement: TodoToolset 任务追踪
系统 SHALL 为每个 Agent（主 Agent 和 Sub-Agent）提供独立的 TodoToolset，用于追踪执行进度。任务状态 SHALL 通过事件流推送到前端。

#### Scenario: 任务创建和更新
- **WHEN** Agent 调用 todo_create("分析数据") 和 todo_update(id, status="completed")
- **THEN** 系统 SHALL 记录任务状态变更，并推送 todo_updated 事件到前端

#### Scenario: Sub-Agent 独立 Todo
- **WHEN** Sub-Agent 创建 Todo 任务
- **THEN** 该 Todo SHALL 隶属于 Sub-Agent 的独立上下文，不与主 Agent 的 Todo 混淆