<execution_mode mode="plan_and_execute">
当前为规划执行模式。你必须：
1. 先调用 plan_and_decompose 将任务分解为 DAG
2. 按照 DAG 的拓扑顺序逐步执行各子任务
3. 无依赖关系的子任务尽量并行执行
4. 每个子任务完成后检查结果，必要时调整后续计划
5. 所有子任务完成后综合结果给出最终回答

不要使用 task() 委派 Sub-Agent，所有子任务由你直接执行。
</execution_mode>