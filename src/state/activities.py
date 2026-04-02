"""Temporal Activity 定义

每个 Activity 是一个可重试的原子操作单元。
"""

# 标准库
from typing import Any, Dict, List, Optional

# 第三方库
from temporalio import activity

# 本地模块
from src.core.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def plan_task(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """规划任务 DAG

    Args:
        query: 用户请求
        context: 附加上下文

    Returns:
        DAG 字典
    """
    from src.orchestrator.planner import plan_tasks

    logger.info(f"[Activity:plan_task] 开始规划 | query_len={len(query)}")

    dag = await plan_tasks(query, context)
    return dag.model_dump()


@activity.defn
async def execute_native_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    """执行可信 Worker

    Args:
        task: 任务节点字典

    Returns:
        WorkerResult 字典
    """
    from src.orchestrator.router import route_task
    from src.schemas.agent import TaskNode

    task_node = TaskNode(**task)
    worker_name = route_task(task_node)

    logger.info(
        f"[Activity:execute_native_worker] | "
        f"task_id={task_node.task_id} worker={worker_name}"
    )

    # 根据 worker_name 实例化对应 Worker
    worker = _get_worker(worker_name)
    if not worker:
        return {
            "task_id": task_node.task_id,
            "success": False,
            "error": f"Worker '{worker_name}' 未注册",
        }

    result = await worker.execute(task_node)
    return result.model_dump()


@activity.defn
async def execute_sandbox_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    """执行沙箱 Worker

    Args:
        task: 任务节点字典

    Returns:
        SandboxResult 字典
    """
    from src.schemas.sandbox import SandboxTask
    from src.workers.sandbox.sandbox_worker import SandboxWorker

    logger.info(
        f"[Activity:execute_sandbox_worker] | task_id={task.get('task_id')}"
    )

    sandbox_task = SandboxTask(
        task_id=task.get("task_id", ""),
        instruction=task.get("description", ""),
        context_files=task.get("input_data", {}).get("context_files", {}),
    )

    worker = SandboxWorker()
    result = await worker.execute(sandbox_task)
    return result.model_dump()


@activity.defn
async def collect_results(
    query: str,
    worker_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """整合所有 Worker 结果，生成最终响应

    Args:
        query: 原始用户请求
        worker_results: 所有 Worker 执行结果

    Returns:
        最终编排输出字典
    """
    logger.info(
        f"[Activity:collect_results] | "
        f"query_len={len(query)} results_count={len(worker_results)}"
    )

    # 汇总成功/失败
    successful = [r for r in worker_results if r.get("success")]
    failed = [r for r in worker_results if not r.get("success")]

    # 构建最终答案
    if not successful and failed:
        answer = f"任务执行失败: {failed[0].get('error', '未知错误')}"
    else:
        data_parts = []
        for r in successful:
            data = r.get("data")
            if data:
                data_parts.append(str(data)[:500])
        answer = "\n".join(data_parts) if data_parts else "任务已完成"

    return {
        "answer": answer,
        "worker_results": worker_results,
        "trace_id": "",
        "a2ui_frames": [],
    }


def _get_worker(worker_name: str):
    """根据名称获取 Worker 实例"""
    from src.workers.native.api_call_worker import APICallWorker
    from src.workers.native.db_query_worker import DBQueryWorker
    from src.workers.native.rag_worker import RAGWorker

    registry = {
        "rag_worker": RAGWorker,
        "db_query_worker": DBQueryWorker,
        "api_call_worker": APICallWorker,
    }

    worker_cls = registry.get(worker_name)
    if worker_cls:
        return worker_cls()
    return None
