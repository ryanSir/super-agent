# Proposal: 修复 planner_agent 输出验证失败

## 背景

用户输入"帮我搜索一下 2024 年大语言模型的最新进展"时，`planner_agent` 报错：
`任务规划失败: Exceeded maximum retries (1) for output validation`

根本原因：LLM 生成了 `web_search` 之类的 task_type，但 `TaskType` 枚举只有 5 个合法值，Pydantic 验证失败。`planner_agent` 默认 retries=1，一次失败后直接抛出异常。

## 目标

1. 让 planner prompt 明确约束 LLM 只能使用枚举中的合法值
2. 增加 planner_agent 重试次数，提升容错能力

## Non-goals

- 不新增 `web_search` task_type（当前没有对应 Worker）
- 不修改 TaskType 枚举
- 不修改路由逻辑
