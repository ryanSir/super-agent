## ADDED Requirements

### Requirement: Sub-Agent 声明式配置

系统 SHALL 通过 SubAgentConfig 声明式定义 Sub-Agent 角色，传给主 Agent 的 subagents 参数。每个 SubAgentConfig 包含：name、description、instructions、model、工具列表、deepagents 能力开关。

预置三个角色：
- researcher：信息检索与综合分析，可用工具为 execute_rag_search/execute_api_call/execute_skill/search_skills/execute_sandbox
- analyst：数据分析与可视化，可用工具为 execute_db_query/execute_rag_search/execute_sandbox/emit_chart
- writer：报告与文档撰写，可用工具为 execute_skill/execute_sandbox/emit_chart，启用 filesystem

#### Scenario: 创建 Research Sub-Agent
- **WHEN** SubAgentFactory 创建 researcher 配置
- **THEN** SubAgentConfig.name 为 "researcher"，include_todo 为 True，context_manager 为 True，tools 包含 5 个桥接工具

#### Scenario: Sub-Agent 工具范围限定
- **WHEN** analyst Sub-Agent 执行任务
- **THEN** analyst 只能调用其配置中声明的 4 个桥接工具，无法调用 execute_skill 或 search_skills

### Requirement: Agent-as-Tool 委派

主 Agent SHALL 通过 deepagents 内置的 SubAgentToolset 委派任务给 Sub-Agent。可用操作：
- task(agent_name, instruction)：异步委派任务
- check_task(task_id)：检查任务状态
- list_active_tasks()：列出活跃任务
- cancel_task(task_id)：取消任务

主 Agent 的 LLM 根据 prompt_prefix 中的角色描述自主决定何时委派、委派给谁。

#### Scenario: 委派 Research 任务
- **WHEN** 主 Agent 在 SUB_AGENT 模式下需要搜索信息
- **THEN** 主 Agent 调用 task("researcher", "搜索最近的AI论文...")，SubAgentToolset 自动创建独立的 Research Sub-Agent 执行

#### Scenario: 并行委派多个任务
- **WHEN** 主 Agent 需要同时调研三个竞品
- **THEN** 主 Agent 连续调用三次 task("researcher", ...)，三个 Sub-Agent 并行执行

#### Scenario: 检查委派任务状态
- **WHEN** 主 Agent 委派任务后需要等待结果
- **THEN** 主 Agent 调用 check_task(task_id) 获取任务状态和结果

### Requirement: Sub-Agent 上下文隔离

每个 Sub-Agent SHALL 拥有独立的上下文，不共享主 Agent 的 message_history。deepagents 通过 clone_for_subagent() 实现隔离。

Sub-Agent 的详细中间结果在其内部消化，返回给主 Agent 的是精炼后的摘要结果，保持主 Agent 上下文干净。

#### Scenario: 上下文独立
- **WHEN** Research Sub-Agent 执行过程中产生大量工具调用结果
- **THEN** 这些结果只存在于 Research Sub-Agent 的上下文中，主 Agent 的 message_history 只包含委派调用和最终返回值

#### Scenario: Sub-Agent 上下文压缩
- **WHEN** Sub-Agent 的上下文接近 context_manager_max_tokens（100,000）
- **THEN** SummarizationProcessor 自动触发压缩，保留近期消息，摘要早期消息

### Requirement: Worker 桥接工具

系统 SHALL 提供桥接层（bridge.py），将现有 Workers 和 Skills 包装为 deepagents 兼容的工具函数。

桥接工具列表：
- execute_rag_search：调用 RAGWorker 向量检索
- execute_db_query：调用 DBQueryWorker SQL 只读查询
- execute_api_call：调用 APICallWorker HTTP 请求
- execute_sandbox：调用 SandboxWorker E2B 沙箱执行
- execute_skill：执行已注册的 Skill
- search_skills：搜索可用 Skills
- emit_chart：渲染 ECharts 图表到前端
- recall_memory：从 Redis 检索用户记忆
- plan_and_decompose：调用 Planner Agent 生成 ExecutionDAG

桥接工具持有 Worker 实例引用（进程内），不产生额外网络开销。

#### Scenario: 桥接工具调用 Worker
- **WHEN** Sub-Agent 调用 execute_rag_search(query="AI论文", top_k=5)
- **THEN** 桥接工具内部构建 TaskNode，调用 RAGWorker.execute()，返回 WorkerResult.model_dump()

#### Scenario: 桥接工具错误处理
- **WHEN** Worker 执行失败（WorkerResult.success=False）
- **THEN** 桥接工具返回包含 error 字段的 dict，Sub-Agent 的 LLM 可据此决定重试或降级

### Requirement: Sub-Agent 内部任务规划

每个 Sub-Agent SHALL 启用 TodoToolset（include_todo=True），支持内部任务分解和进度追踪。Sub-Agent 可自主将复杂子任务拆解为多个步骤并逐步执行。

#### Scenario: Research Sub-Agent 内部规划
- **WHEN** Research Sub-Agent 收到 "搜索最近三年的 AI Agent 论文并综合分析"
- **THEN** Sub-Agent 使用 TodoToolset 规划步骤（如：1.搜索论文 2.筛选相关 3.提取关键信息 4.综合分析），逐步执行并追踪进度
