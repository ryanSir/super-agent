"""数据库查询 Worker

安全执行 SQL 查询，返回结构化结果。
"""

# 标准库
from typing import Any, Dict, List, Optional

# 第三方库
import httpx

# 本地模块
from src.core.exceptions import WorkerError
from src.core.logging import get_logger
from src.config.settings import get_settings
from src.schemas.agent import TaskNode, WorkerResult
from src.workers.base import BaseWorker

logger = get_logger(__name__)


class DBQueryWorker(BaseWorker):
    """数据库查询 Worker

    通过内部数据平台 API 安全执行 SQL 查询，
    避免直接暴露数据库连接给 Agent。

    Args:
        api_base_url: 数据平台 API 地址
    """

    def __init__(self, api_base_url: Optional[str] = None) -> None:
        super().__init__(name="db_query_worker")
        settings = get_settings()
        self._api_base_url = api_base_url or settings.database.dsn
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> None:
        """懒初始化 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行数据库查询

        task.input_data 期望字段：
            - sql: SQL 查询语句
            - params: 查询参数（可选）
            - database: 目标数据库（可选）
        """
        sql = task.input_data.get("sql", "")
        params = task.input_data.get("params", {})
        database = task.input_data.get("database", "default")

        if not sql:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="SQL 查询语句不能为空",
            )

        # 安全检查：禁止危险操作
        sql_upper = sql.strip().upper()
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"]
        for keyword in dangerous_keywords:
            if sql_upper.startswith(keyword):
                return WorkerResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"禁止执行 {keyword} 操作，仅允许 SELECT 查询",
                )

        await self._ensure_client()

        try:
            # 通过数据平台 API 执行查询
            response = await self._http_client.post(
                f"{self._api_base_url}/query",
                json={
                    "sql": sql,
                    "params": params,
                    "database": database,
                },
            )
            response.raise_for_status()
            result_data = response.json()

            logger.info(
                f"[DBQueryWorker] 查询完成 | "
                f"task_id={task.task_id} database={database} "
                f"rows={len(result_data.get('rows', []))}"
            )

            return WorkerResult(
                task_id=task.task_id,
                success=True,
                data=result_data,
                metadata={"database": database, "sql": sql[:200]},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[DBQueryWorker] 查询失败 | "
                f"task_id={task.task_id} status={e.response.status_code}",
                exc_info=True,
            )
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"数据库查询失败: HTTP {e.response.status_code}",
            )
        except Exception as e:
            raise WorkerError(
                f"数据库查询异常: {e}",
                context={"task_id": task.task_id, "sql": sql[:200]},
            ) from e

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
