"""Worker 基类和 Protocol 测试"""

import pytest

from src.schemas.agent import TaskNode, TaskType, WorkerResult
from src.workers.base import BaseWorker, WorkerProtocol
from src.workers.native.rag_worker import RAGWorker
from src.workers.native.db_query_worker import DBQueryWorker
from src.workers.native.api_call_worker import APICallWorker


class TestWorkerProtocol:
    def test_rag_worker_implements_protocol(self):
        assert isinstance(RAGWorker(), WorkerProtocol)

    def test_db_query_worker_implements_protocol(self):
        assert isinstance(DBQueryWorker(), WorkerProtocol)

    def test_api_call_worker_implements_protocol(self):
        assert isinstance(APICallWorker(), WorkerProtocol)

    def test_worker_names(self):
        assert RAGWorker().name == "rag_worker"
        assert DBQueryWorker().name == "db_query_worker"
        assert APICallWorker().name == "api_call_worker"


class MockWorker(BaseWorker):
    """测试用 Mock Worker"""

    def __init__(self):
        super().__init__(name="mock_worker")

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        return WorkerResult(
            task_id=task.task_id,
            success=True,
            data={"mock": True},
        )


class TestBaseWorker:
    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        worker = MockWorker()
        task = TaskNode(task_id="t1", task_type=TaskType.RAG_RETRIEVAL, description="test")
        result = await worker.execute(task)
        assert result.success is True
        assert result.data == {"mock": True}

    @pytest.mark.asyncio
    async def test_execute_catches_exceptions(self):
        class FailingWorker(BaseWorker):
            def __init__(self):
                super().__init__(name="failing_worker")

            async def _do_execute(self, task):
                raise RuntimeError("boom")

        worker = FailingWorker()
        task = TaskNode(task_id="t1", task_type=TaskType.RAG_RETRIEVAL, description="test")
        result = await worker.execute(task)
        assert result.success is False
        assert "boom" in result.error
