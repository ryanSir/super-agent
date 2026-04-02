"""测试 RedisMemoryStorage"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.schema import Fact, MemoryData, UserProfile
from src.memory.storage import RedisMemoryStorage


def _make_storage() -> RedisMemoryStorage:
    return RedisMemoryStorage(key_prefix="test_memory")


@pytest.mark.asyncio
@patch("src.memory.storage.get_redis_client", new_callable=AsyncMock)
async def test_load_empty_user(mock_redis_fn):
    """无记忆用户返回空结构"""
    mock_redis = AsyncMock()
    mock_redis.hgetall.return_value = {}
    mock_redis.zrevrange.return_value = []
    mock_redis.get.return_value = None
    mock_redis_fn.return_value = mock_redis

    storage = _make_storage()
    data = await storage.load("user-1")

    assert data.profile.work_context == ""
    assert data.facts == []
    assert data.updated_at is None


@pytest.mark.asyncio
@patch("src.memory.storage.get_redis_client", new_callable=AsyncMock)
async def test_load_with_data(mock_redis_fn):
    """有数据时正确解析"""
    mock_redis = AsyncMock()
    mock_redis.hgetall.return_value = {
        "work_context": "数据科学家",
        "personal_context": "偏好简洁",
        "top_of_mind": "日志分析",
    }
    fact_json = json.dumps({"content": "用户使用 Milvus", "source_session_id": "s1"})
    mock_redis.zrevrange.return_value = [(fact_json, 1700000000.0)]
    mock_redis.get.return_value = "2024-01-01T00:00:00"
    mock_redis_fn.return_value = mock_redis

    storage = _make_storage()
    data = await storage.load("user-1")

    assert data.profile.work_context == "数据科学家"
    assert len(data.facts) == 1
    assert data.facts[0].content == "用户使用 Milvus"


@pytest.mark.asyncio
@patch("src.memory.storage.get_redis_client", new_callable=AsyncMock)
async def test_save_writes_to_redis(mock_redis_fn):
    """保存时正确写入 Redis"""
    mock_redis = AsyncMock()
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis_fn.return_value = mock_redis

    storage = _make_storage()
    data = MemoryData(
        profile=UserProfile(work_context="工程师"),
        facts=[Fact(content="fact1", source_session_id="s1")],
    )

    result = await storage.save("user-1", data)

    assert result is True
    mock_pipe.hset.assert_called_once()
    mock_pipe.zadd.assert_called_once()
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
@patch("src.memory.storage.get_redis_client", new_callable=AsyncMock)
async def test_load_redis_failure_returns_empty(mock_redis_fn):
    """Redis 连接失败时返回空记忆"""
    mock_redis_fn.side_effect = ConnectionError("Redis down")

    storage = _make_storage()
    data = await storage.load("user-1")

    assert data.profile.work_context == ""
    assert data.facts == []


@pytest.mark.asyncio
@patch("src.memory.storage.get_redis_client", new_callable=AsyncMock)
async def test_delete_removes_keys(mock_redis_fn):
    """删除时移除所有相关 key"""
    mock_redis = AsyncMock()
    mock_redis_fn.return_value = mock_redis

    storage = _make_storage()
    result = await storage.delete("user-1")

    assert result is True
    mock_redis.delete.assert_called_once()
