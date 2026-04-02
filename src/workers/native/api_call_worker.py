"""内部 API 调用 Worker

调用内部微服务 API，携带内网凭证。
"""

# 标准库
from typing import Any, Dict, Optional

# 第三方库
import httpx

# 本地模块
from src.core.exceptions import APICallError
from src.core.logging import get_logger
from src.config.settings import get_settings
from src.schemas.agent import TaskNode, WorkerResult
from src.workers.base import BaseWorker

logger = get_logger(__name__)


class APICallWorker(BaseWorker):
    """内部 API 调用 Worker

    在宿主环境安全调用内部微服务，携带内网凭证和认证信息。

    Args:
        default_base_url: 默认 API 基础地址
        default_headers: 默认请求头
    """

    def __init__(
        self,
        default_base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name="api_call_worker")
        settings = get_settings()
        self._default_base_url = (
            default_base_url or "http://qa-s-core-eureka.patsnap.info/eureka/"
        )
        self._default_headers = default_headers or {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> None:
        """懒初始化 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=60.0,
                headers=self._default_headers,
            )

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """执行 API 调用

        task.input_data 期望字段：
            - url: 完整 URL 或相对路径
            - method: HTTP 方法（GET/POST/PUT/DELETE），默认 GET
            - headers: 额外请求头（可选）
            - body: 请求体（可选）
            - params: URL 查询参数（可选）
        """
        url = task.input_data.get("url", "")
        method = task.input_data.get("method", "GET").upper()
        headers = task.input_data.get("headers", {})
        body = task.input_data.get("body")
        params = task.input_data.get("params")

        if not url:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="API URL 不能为空",
            )

        # 相对路径拼接
        if not url.startswith("http"):
            url = f"{self._default_base_url.rstrip('/')}/{url.lstrip('/')}"

        await self._ensure_client()

        try:
            response = await self._http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ("POST", "PUT", "PATCH") else None,
                params=params,
            )
            response.raise_for_status()

            # 尝试解析 JSON，失败则返回文本
            try:
                result_data = response.json()
            except Exception:
                result_data = {"text": response.text}

            logger.info(
                f"[APICallWorker] 调用完成 | "
                f"task_id={task.task_id} method={method} "
                f"url={url[:80]} status={response.status_code}"
            )

            return WorkerResult(
                task_id=task.task_id,
                success=True,
                data=result_data,
                metadata={"url": url, "method": method, "status": response.status_code},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[APICallWorker] API 调用失败 | "
                f"task_id={task.task_id} url={url[:80]} status={e.response.status_code}",
                exc_info=True,
            )
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=f"API 调用失败: HTTP {e.response.status_code}",
                metadata={"url": url, "status": e.response.status_code},
            )
        except Exception as e:
            raise APICallError(
                f"API 调用异常: {e}",
                context={"task_id": task.task_id, "url": url[:200], "method": method},
            ) from e

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
