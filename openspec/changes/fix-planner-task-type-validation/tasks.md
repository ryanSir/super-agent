# Tasks: 修复 planner 输出验证

## Task 1: 修改 `src/orchestrator/prompts/planning.py` — 明确 task_type 合法值

将 prompt 中 task_type 描述改为枚举约束，明确列出 5 个合法值，并说明 `api_call` 覆盖搜索场景。

## Task 2: 修改 `src/orchestrator/planner.py` — planner_agent 增加 retries=3
