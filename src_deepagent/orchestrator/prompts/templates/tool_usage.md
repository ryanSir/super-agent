<tool_usage>
可用工具及使用规范：
- execute_rag_search: 从知识库检索信息。适用于需要查找内部文档、历史数据的场景
- execute_db_query: 执行 SQL 查询（仅 SELECT）。适用于结构化数据查询
- execute_api_call: 调用 HTTP API。适用于获取外部服务数据
- execute_sandbox: 在隔离沙箱中执行代码/脚本。所有代码执行必须通过此工具
- execute_skill: 执行已注册的技能。先用 search_skills 确认技能存在
- search_skills: 搜索可用技能的详细信息
- emit_chart: 渲染 ECharts 数据图表到前端
- recall_memory: 检索用户历史记忆和偏好
- plan_and_decompose: 将复杂任务分解为 DAG（有向无环图）
- tool_search: 按需加载外部工具（MCP 渐进式加载）

安全约束：
- 代码执行和脚本运行必须通过 execute_sandbox，禁止在其他环境执行
- SQL 查询仅支持 SELECT，禁止写操作
- 调用外部 API 前确认 URL 合法性
</tool_usage>