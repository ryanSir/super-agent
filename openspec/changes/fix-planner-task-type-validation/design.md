# Design: 修复 planner 输出验证

## 两处改动

### 1. `src/orchestrator/prompts/planning.py` — 明确枚举约束

在 prompt 的"输出要求"中，将 task_type 的描述从自由文本改为明确列出合法值：

```
- task_type: 任务类型，必须是以下之一：
  - rag_retrieval（知识库检索）
  - db_query（数据库查询）
  - api_call（外部 API 调用，包括搜索、第三方服务）
  - sandbox_coding（代码生成与执行）
  - data_analysis（数据分析）
```

`api_call` 覆盖"搜索"场景，LLM 不会再生成 `web_search`。

### 2. `src/orchestrator/planner.py` — 增加重试次数

`planner_agent` 构造时加 `retries=3`（当前默认为 1）。
