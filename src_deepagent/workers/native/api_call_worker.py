"""APICallWorker — HTTP API 调用

调用内部微服务 HTTP 接口。
"""

from __future__ import annotations

from typing import Any

import httpx

from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import TaskNode, WorkerResult
from src_deepagent.workers.base import BaseWorker

logger = get_logger(__name__)


class APICallWorker(BaseWorker):
    """HTTP API 调用 Worker"""

    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "api_call_worker"

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行 HTTP 请求"""
        url = task.input_data.get("url", "")
        method = task.input_data.get("method", "GET").upper()
        headers = task.input_data.get("headers", {})
        body = task.input_data.get("body")
        params = task.input_data.get("params")

        if not url:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="缺少 url 参数",
            )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    params=params,
                )

            success = 200 <= response.status_code < 400
            data: dict[str, Any] = {
                "status_code": response.status_code,
                "url": url,
                "method": method,
            }

            # 尝试解析 JSON 响应
            try:
                data["body"] = response.json()
            except Exception:
                data["body"] = response.text[:5000]

            return WorkerResult(
                task_id=task.task_id,
                success=success,
                data=data,
                error="" if success else f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"HTTP 请求超时 ({self._timeout}s): {url}",
            )
        except Exception as e:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"HTTP 请求失败: {e}",
            )
