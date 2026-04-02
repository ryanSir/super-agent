"""任务路由分发

根据 TaskNode.risk_level 将任务路由到可信 Worker 或沙箱 Worker。
"""

# 标准库
from typing import Dict, List

# 本地模块
from src.core.exceptions import RoutingError
from src.core.logging import get_logger
from src.schemas.agent import RiskLevel, TaskNode, TaskType

logger = get_logger(__name__)

# 任务类型 → 默认 Worker 名称映射
WORKER_REGISTRY: Dict[TaskType, str] = {
    TaskType.RAG_RETRIEVAL: "rag_worker",
    TaskType.DB_QUERY: "db_query_worker",
    TaskType.API_CALL: "api_call_worker",
    TaskType.SANDBOX_CODING: "sandbox_worker",
    TaskType.DATA_ANALYSIS: "sandbox_worker",
}


def route_task(task: TaskNode) -> str:
    """根据任务属性路由到目标 Worker

    Args:
        task: 任务节点

    Returns:
        Worker 名称

    Raises:
        RoutingError: 无法找到匹配的 Worker
    """
    # 强制规则：dangerous 任务必须走沙箱
    if task.risk_level == RiskLevel.DANGEROUS:
        logger.info(
            f"[Router] 路由到沙箱 Worker | "
            f"task_id={task.task_id} task_type={task.task_type} risk=dangerous"
        )
        return "sandbox_worker"

    # 按任务类型查找 Worker
    worker_name = WORKER_REGISTRY.get(task.task_type)
    if not worker_name:
        raise RoutingError(
            f"未找到匹配的 Worker: task_type={task.task_type}",
            context={"task_id": task.task_id, "task_type": task.task_type.value},
        )

    logger.info(
        f"[Router] 路由到 {worker_name} | "
        f"task_id={task.task_id} task_type={task.task_type} risk={task.risk_level}"
    )
    return worker_name


def classify_tasks(tasks: List[TaskNode]) -> Dict[str, List[TaskNode]]:
    """将任务列表按 Worker 分组

    Args:
        tasks: 任务节点列表

    Returns:
        Worker 名称 → 任务列表的映射
    """
    groups: Dict[str, List[TaskNode]] = {}
    for task in tasks:
        worker = route_task(task)
        groups.setdefault(worker, []).append(task)
    return groups
