"""Temporal Workflow 定义

AgentWorkflow：接收请求 → 规划 → 分发执行 → 回收结果。
支持宕机恢复和重试。
"""

# 标准库
from datetime import timedelta
from typing import Any, Dict, List, Optional

# 第三方库
from temporalio import workflow

# 注意：Workflow 内不能直接导入非确定性模块
# Activity 通过 workflow.execute_activity 调用
with workflow.unsafe.imports_passed_through():
    from src.schemas.agent import ExecutionDAG, OrchestratorOutput, TaskNode, WorkerResult


@workflow.defn
class AgentWorkflow:
    """智能体主工作流

    编排完整的 Plan-and-Execute 流程：
    1. 规划任务 DAG
    2. 按拓扑序执行子任务（可信/沙箱）
    3. 整合结果生成最终响应
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """工作流入口

        Args:
            params: {
                "query": str,
                "session_id": str,
                "trace_id": str,
                "context": dict,
            }

        Returns:
            编排结果字典
        """
        query = params["query"]
        session_id = params.get("session_id", "")
        trace_id = params.get("trace_id", "")

        # 1. 规划阶段
        dag_dict = await workflow.execute_activity(
            "plan_task",
            args=[query, params.get("context", {})],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=2),
            ),
        )

        tasks = dag_dict.get("tasks", [])
        if not tasks:
            return {
                "answer": "无法拆解任务，请尝试更具体的描述。",
                "worker_results": [],
                "trace_id": trace_id,
            }

        # 2. 按依赖关系分层执行
        worker_results = []
        completed_ids = set()

        # 简单拓扑排序：按 depends_on 分层
        remaining = list(tasks)
        max_rounds = 10

        for _ in range(max_rounds):
            if not remaining:
                break

            # 找出当前可执行的任务（依赖已完成）
            ready = [
                t for t in remaining
                if all(dep in completed_ids for dep in t.get("depends_on", []))
            ]

            if not ready:
                break

            # 并行执行当前层的所有任务
            batch_results = []
            for task in ready:
                risk = task.get("risk_level", "safe")
                activity_name = (
                    "execute_sandbox_worker" if risk == "dangerous"
                    else "execute_native_worker"
                )

                result = await workflow.execute_activity(
                    activity_name,
                    args=[task],
                    start_to_close_timeout=timedelta(seconds=300),
                    retry_policy=workflow.RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=5),
                    ),
                )
                batch_results.append(result)

            worker_results.extend(batch_results)
            for task in ready:
                completed_ids.add(task["task_id"])
            remaining = [t for t in remaining if t["task_id"] not in completed_ids]

        # 3. 整合结果
        final_result = await workflow.execute_activity(
            "collect_results",
            args=[query, worker_results],
            start_to_close_timeout=timedelta(seconds=60),
        )

        return final_result
