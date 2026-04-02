"""测试 MemoryUpdater"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.schema import Fact, MemoryData, UserProfile
from src.memory.updater import MemoryUpdater


def _make_updater() -> MemoryUpdater:
    return MemoryUpdater(max_facts=5, model_alias="fast")


def _make_messages():
    return [
        {"role": "user", "content": "我是数据科学家，帮我分析日志"},
        {"role": "assistant", "content": "好的，我来帮你分析日志数据。"},
    ]


@pytest.mark.asyncio
@patch("src.memory.updater.MemoryUpdater._release_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._acquire_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_facts", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_profile_update", new_callable=AsyncMock)
@patch("src.memory.updater.get_memory_storage")
async def test_update_extracts_and_saves(
    mock_storage_fn, mock_profile, mock_facts, mock_lock, mock_unlock
):
    """正常更新：提取 profile 和 facts 并保存"""
    mock_storage = MagicMock()
    mock_storage.load = AsyncMock(return_value=MemoryData())
    mock_storage.save = AsyncMock(return_value=True)
    mock_storage_fn.return_value = mock_storage

    mock_lock.return_value = "lock-value"
    mock_profile.return_value = {"work_context": "数据科学家"}
    mock_facts.return_value = [
        Fact(content="用户专注于日志分析", source_session_id="s1")
    ]

    updater = _make_updater()
    result = await updater.update("user-1", _make_messages(), "s1")

    assert result is True
    mock_storage.save.assert_called_once()
    saved_data = mock_storage.save.call_args[0][1]
    assert saved_data.profile.work_context == "数据科学家"
    assert len(saved_data.facts) == 1


@pytest.mark.asyncio
@patch("src.memory.updater.MemoryUpdater._release_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._acquire_lock", new_callable=AsyncMock)
async def test_lock_failure_skips_update(mock_lock, mock_unlock):
    """获取锁失败时跳过更新"""
    mock_lock.return_value = None

    updater = _make_updater()
    result = await updater.update("user-1", _make_messages(), "s1")

    assert result is False


@pytest.mark.asyncio
@patch("src.memory.updater.MemoryUpdater._release_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._acquire_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_facts", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_profile_update", new_callable=AsyncMock)
@patch("src.memory.updater.get_memory_storage")
async def test_fact_dedup(
    mock_storage_fn, mock_profile, mock_facts, mock_lock, mock_unlock
):
    """重复 fact 更新时间戳而非重复添加"""
    existing = MemoryData(
        facts=[Fact(content="已有事实", source_session_id="s0")]
    )
    mock_storage = MagicMock()
    mock_storage.load = AsyncMock(return_value=existing)
    mock_storage.save = AsyncMock(return_value=True)
    mock_storage_fn.return_value = mock_storage

    mock_lock.return_value = "lock-value"
    mock_profile.return_value = {}
    mock_facts.return_value = [
        Fact(content="已有事实", source_session_id="s1")
    ]

    updater = _make_updater()
    await updater.update("user-1", _make_messages(), "s1")

    saved_data = mock_storage.save.call_args[0][1]
    assert len(saved_data.facts) == 1  # 没有重复


@pytest.mark.asyncio
@patch("src.memory.updater.MemoryUpdater._release_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._acquire_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_facts", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_profile_update", new_callable=AsyncMock)
@patch("src.memory.updater.get_memory_storage")
async def test_fact_eviction(
    mock_storage_fn, mock_profile, mock_facts, mock_lock, mock_unlock
):
    """超过上限时淘汰最旧的 fact"""
    existing = MemoryData(
        facts=[
            Fact(content=f"fact-{i}", source_session_id="s0",
                 created_at=datetime(2024, 1, i + 1))
            for i in range(5)
        ]
    )
    mock_storage = MagicMock()
    mock_storage.load = AsyncMock(return_value=existing)
    mock_storage.save = AsyncMock(return_value=True)
    mock_storage_fn.return_value = mock_storage

    mock_lock.return_value = "lock-value"
    mock_profile.return_value = {}
    mock_facts.return_value = [
        Fact(content="new-fact", source_session_id="s1")
    ]

    updater = _make_updater()  # max_facts=5
    await updater.update("user-1", _make_messages(), "s1")

    saved_data = mock_storage.save.call_args[0][1]
    assert len(saved_data.facts) == 5  # 淘汰了最旧的一条


@pytest.mark.asyncio
@patch("src.memory.updater.MemoryUpdater._release_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._acquire_lock", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_facts", new_callable=AsyncMock)
@patch("src.memory.updater.MemoryUpdater._extract_profile_update", new_callable=AsyncMock)
@patch("src.memory.updater.get_memory_storage")
async def test_llm_failure_graceful(
    mock_storage_fn, mock_profile, mock_facts, mock_lock, mock_unlock
):
    """LLM 提取失败时不崩溃"""
    mock_storage = MagicMock()
    mock_storage.load = AsyncMock(return_value=MemoryData())
    mock_storage_fn.return_value = mock_storage

    mock_lock.return_value = "lock-value"
    mock_profile.side_effect = RuntimeError("LLM timeout")
    mock_facts.side_effect = RuntimeError("LLM timeout")

    updater = _make_updater()
    result = await updater.update("user-1", _make_messages(), "s1")

    # 两个都失败，但不崩溃
    assert result is False
