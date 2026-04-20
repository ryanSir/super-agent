<tool_usage>
可用工具及使用规范：
- execute_sandbox: 在隔离沙箱中执行代码/脚本。所有代码执行必须通过此工具
- execute_skill: 执行已注册的技能。先用 search_skills 确认技能存在
- search_skills: 搜索可用技能的详细信息
- emit_chart: 渲染 ECharts 数据图表到前端（A2UI 协议）。当回答中包含数值对比、趋势变化、占比分布等可视化数据时，必须调用此工具生成图表。支持 bar（柱状图）、line（折线图）、pie（饼图）、scatter（散点图）
- plan_and_decompose: 将复杂任务分解为 DAG（有向无环图）
- baidu_search: 网络搜索，通过百度 AI 搜索引擎检索网页信息。适用于需要查找实时资讯、新闻、技术动态等场景

MCP 外部工具通过 pydantic-ai toolsets 自动注入，可直接按名称调用。

安全约束：
- 代码执行和脚本运行必须通过 execute_sandbox，禁止在其他环境执行
- SQL 查询仅支持 SELECT，禁止写操作
</tool_usage>