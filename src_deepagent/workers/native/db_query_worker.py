"""DBQueryWorker — SQL 只读查询

执行 SELECT 查询，禁止写操作（DROP/DELETE/TRUNCATE/ALTER/INSERT/UPDATE）。
"""

from __future__ import annotations

import re
from typing import Any

from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import TaskNode, WorkerResult
from src_deepagent.workers.base import BaseWorker

logger = get_logger(__name__)

# 禁止的 SQL 关键词（大写匹配）
_FORBIDDEN_KEYWORDS = frozenset({
    "DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
})

_FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


class DBQueryWorker(BaseWorker):
    """SQL 只读查询 Worker"""

    def __init__(self, connection_string: str = "") -> None:
        self._connection_string = connection_string

    @property
    def name(self) -> str:
        return "db_query_worker"

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行 SQL 查询"""
        sql = task.input_data.get("sql", "").strip()

        if not sql:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="缺少 sql 参数",
            )

        # 安全校验：只允许 SELECT
        violation = self._validate_sql(sql)
        if violation:
            logger.warning(f"SQL 安全校验失败 | sql={sql[:100]} violation={violation}")
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"SQL 安全校验失败: 禁止使用 {violation}",
            )

        try:
            rows = await self._execute_query(sql)
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                data={"rows": rows, "row_count": len(rows), "sql": sql},
            )
        except Exception as e:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"SQL 执行失败: {e}",
            )

    def _validate_sql(self, sql: str) -> str | None:
        """校验 SQL 安全性，返回违规关键词或 None"""
        match = _FORBIDDEN_PATTERN.search(sql)
        return match.group(0).upper() if match else None

    async def _execute_query(self, sql: str) -> list[dict]:
        """执行查询（子类或外部注入实际数据库连接）"""
        # TODO: 接入实际数据库连接池
        logger.info(f"执行 SQL | sql={sql[:200]}")
        return []
