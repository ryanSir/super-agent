"""RAGWorker — Milvus 向量检索

从 Milvus 向量数据库中检索相关文档片段。
"""

from __future__ import annotations

from typing import Any

from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import TaskNode, WorkerResult
from src_deepagent.workers.base import BaseWorker

logger = get_logger(__name__)


class RAGWorker(BaseWorker):
    """Milvus 向量检索 Worker"""

    def __init__(self, collection: str = "documents") -> None:
        self._collection = collection
        self._client: Any = None

    @property
    def name(self) -> str:
        return "rag_worker"

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行向量检索"""
        query = task.input_data.get("query", "")
        top_k = task.input_data.get("top_k", 5)

        if not query:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="缺少 query 参数",
            )

        try:
            client = self._get_client()
            results = await self._search(client, query, top_k)
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                data={"documents": results, "query": query, "top_k": top_k},
            )
        except Exception as e:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"RAG 检索失败: {e}",
            )

    def _get_client(self) -> Any:
        """懒初始化 Milvus 客户端"""
        if self._client is None:
            try:
                from pymilvus import MilvusClient

                from src_deepagent.config.settings import get_settings

                settings = get_settings()
                self._client = MilvusClient(
                    uri=f"http://{settings.milvus.host}:{settings.milvus.port}"
                )
            except ImportError:
                logger.warning("pymilvus 未安装，RAGWorker 不可用")
                raise
        return self._client

    async def _search(self, client: Any, query: str, top_k: int) -> list[dict]:
        """执行向量搜索（同步调用包装为异步）"""
        import asyncio

        def _sync_search() -> list[dict]:
            results = client.search(
                collection_name=self._collection,
                data=[query],
                limit=top_k,
                output_fields=["text", "metadata"],
            )
            return [
                {
                    "text": hit.get("entity", {}).get("text", ""),
                    "score": hit.get("distance", 0.0),
                    "metadata": hit.get("entity", {}).get("metadata", {}),
                }
                for hits in results
                for hit in hits
            ]

        return await asyncio.get_event_loop().run_in_executor(None, _sync_search)
