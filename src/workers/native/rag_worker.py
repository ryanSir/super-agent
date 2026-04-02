"""RAG 检索 Worker

连接 Milvus 向量数据库，执行语义检索，返回结构化文档列表。
"""

# 标准库
from typing import Any, Dict, List, Optional

# 本地模块
from src.core.exceptions import RAGRetrievalError
from src.core.logging import get_logger
from src.schemas.agent import TaskNode, WorkerResult
from src.workers.base import BaseWorker

logger = get_logger(__name__)


class RAGWorker(BaseWorker):
    """RAG 检索 Worker

    在宿主环境安全执行向量检索，携带内网凭证访问 Milvus。

    Args:
        milvus_uri: Milvus 连接地址
        collection_name: 默认集合名称
        top_k: 默认返回条数
    """

    def __init__(
        self,
        milvus_uri: str = "http://localhost:19530",
        collection_name: str = "patents",
        top_k: int = 10,
    ) -> None:
        super().__init__(name="rag_worker")
        self._milvus_uri = milvus_uri
        self._collection_name = collection_name
        self._top_k = top_k
        self._client = None

    async def _ensure_client(self) -> None:
        """懒初始化 Milvus 客户端"""
        if self._client is not None:
            return

        try:
            from pymilvus import MilvusClient

            self._client = MilvusClient(uri=self._milvus_uri)
            logger.info(
                f"[RAGWorker] Milvus 连接成功 | uri={self._milvus_uri}"
            )
        except Exception as e:
            raise RAGRetrievalError(
                f"Milvus 连接失败: {e}",
                context={"uri": self._milvus_uri},
            ) from e

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行向量检索

        task.input_data 期望字段：
            - query: 检索文本
            - collection: 集合名称（可选）
            - top_k: 返回条数（可选）
            - filters: 过滤条件（可选）
        """
        query = task.input_data.get("query", task.description)
        collection = task.input_data.get("collection", self._collection_name)
        top_k = task.input_data.get("top_k", self._top_k)
        filters = task.input_data.get("filters")

        if not query:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="检索 query 不能为空",
            )

        await self._ensure_client()

        try:
            search_params = {
                "collection_name": collection,
                "data": [query],
                "limit": top_k,
                "output_fields": ["id", "title", "abstract", "date"],
            }
            if filters:
                search_params["filter"] = filters

            results = self._client.search(**search_params)

            # 结构化返回
            documents = []
            for hits in results:
                for hit in hits:
                    documents.append({
                        "id": hit.get("id"),
                        "score": hit.get("distance", 0),
                        "title": hit.get("entity", {}).get("title", ""),
                        "abstract": hit.get("entity", {}).get("abstract", ""),
                        "date": hit.get("entity", {}).get("date", ""),
                    })

            logger.info(
                f"[RAGWorker] 检索完成 | "
                f"task_id={task.task_id} collection={collection} "
                f"top_k={top_k} results={len(documents)}"
            )

            return WorkerResult(
                task_id=task.task_id,
                success=True,
                data={"documents": documents, "total": len(documents)},
                metadata={"collection": collection, "top_k": top_k},
            )

        except RAGRetrievalError:
            raise
        except Exception as e:
            raise RAGRetrievalError(
                f"向量检索失败: {e}",
                context={
                    "task_id": task.task_id,
                    "collection": collection,
                    "query": query[:100],
                },
            ) from e
