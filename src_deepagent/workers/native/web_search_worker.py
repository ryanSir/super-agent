"""WebSearchWorker — 网络搜索

直接调用百度千帆 AI 搜索 API，不走沙箱。
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Any

import httpx

from src_deepagent.core.logging import get_logger
from src_deepagent.workers.base import BaseWorker

logger = get_logger(__name__)

_BAIDU_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"


class WebSearchWorker(BaseWorker):
    """百度千帆 AI 搜索"""

    def __init__(self) -> None:
        super().__init__(name="web_search_worker")
        self._api_key = os.getenv("BAIDU_API_KEY", "")
        if not self._api_key:
            logger.warning("BAIDU_API_KEY 未配置，WebSearchWorker 不可用")

    async def _do_execute(self, task: Any) -> Any:
        """执行搜索"""
        data = task.input_data
        query = data["query"]
        count = min(max(data.get("count", 10), 1), 50)
        freshness = data.get("freshness")

        search_filter = _build_time_filter(freshness)

        request_body = {
            "messages": [{"content": query, "role": "user"}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": count}],
            "search_filter": search_filter,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _BAIDU_SEARCH_URL,
                json=request_body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            result = resp.json()

        if "code" in result:
            raise RuntimeError(result.get("message", "百度搜索 API 错误"))

        references = result.get("references", [])
        # 移除 snippet 字段（太长，浪费 token）
        for item in references:
            item.pop("snippet", None)

        return {
            "success": True,
            "query": query,
            "count": len(references),
            "references": references,
        }


async def web_search(
    api_key: str,
    query: str,
    count: int = 10,
    freshness: str | None = None,
) -> dict[str, Any]:
    """独立搜索函数（不依赖 Worker 体系，供 base_tools 直接调用）"""
    if not api_key:
        return {"success": False, "error": "BAIDU_API_KEY 未配置"}

    count = min(max(count, 1), 50)
    search_filter = _build_time_filter(freshness)

    request_body = {
        "messages": [{"content": query, "role": "user"}],
        "search_source": "baidu_search_v2",
        "resource_type_filter": [{"type": "web", "top_k": count}],
        "search_filter": search_filter,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _BAIDU_SEARCH_URL,
                json=request_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            result = resp.json()

        if "code" in result:
            return {"success": False, "error": result.get("message", "API 错误")}

        references = result.get("references", [])
        for item in references:
            item.pop("snippet", None)

        return {
            "success": True,
            "data": {
                "query": query,
                "count": len(references),
                "references": references,
            },
        }
    except httpx.TimeoutException:
        return {"success": False, "error": "搜索超时"}
    except Exception as e:
        return {"success": False, "error": f"搜索失败: {e}"}


def _build_time_filter(freshness: str | None) -> dict:
    """构建时间过滤条件"""
    if not freshness:
        return {}

    now = datetime.now()
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    period_map = {
        "pd": timedelta(days=1),
        "pw": timedelta(days=7),
        "pm": timedelta(days=31),
        "py": timedelta(days=365),
    }

    if freshness in period_map:
        start_date = (now - period_map[freshness]).strftime("%Y-%m-%d")
        return {"range": {"page_time": {"gte": start_date, "lt": end_date}}}

    # 自定义范围：2024-01-01to2024-06-01
    if re.match(r"\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}", freshness):
        start, end = freshness.split("to")
        return {"range": {"page_time": {"gte": start, "lt": end}}}

    return {}
