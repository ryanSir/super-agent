"""Orchestrator 路由和规划测试"""

from src.orchestrator.router import classify_tasks, route_task, WORKER_REGISTRY
from src.schemas.agent import RiskLevel, TaskNode, TaskType


class TestRouter:
    def test_safe_rag_task_routes_to_rag_worker(self):
        task = TaskNode(task_id="t1", task_type=TaskType.RAG_RETRIEVAL, description="检索")
        assert route_task(task) == "rag_worker"

    def test_safe_db_task_routes_to_db_worker(self):
        task = TaskNode(task_id="t2", task_type=TaskType.DB_QUERY, description="查询")
        assert route_task(task) == "db_query_worker"

    def test_safe_api_task_routes_to_api_worker(self):
        task = TaskNode(task_id="t3", task_type=TaskType.API_CALL, description="调用")
        assert route_task(task) == "api_call_worker"

    def test_dangerous_task_always_routes_to_sandbox(self):
        task = TaskNode(
            task_id="t4",
            task_type=TaskType.RAG_RETRIEVAL,
            risk_level=RiskLevel.DANGEROUS,
            description="高危检索",
        )
        assert route_task(task) == "sandbox_worker"

    def test_sandbox_coding_routes_to_sandbox(self):
        task = TaskNode(task_id="t5", task_type=TaskType.SANDBOX_CODING, description="编码")
        assert route_task(task) == "sandbox_worker"

    def test_classify_tasks_groups_correctly(self):
        tasks = [
            TaskNode(task_id="t1", task_type=TaskType.RAG_RETRIEVAL, description="检索"),
            TaskNode(task_id="t2", task_type=TaskType.DB_QUERY, description="查询"),
            TaskNode(task_id="t3", task_type=TaskType.SANDBOX_CODING, description="编码"),
        ]
        groups = classify_tasks(tasks)
        assert "rag_worker" in groups
        assert "db_query_worker" in groups
        assert "sandbox_worker" in groups
        assert len(groups["rag_worker"]) == 1
