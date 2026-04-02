"""pytest 全局 fixtures"""

# 标准库
import asyncio
from typing import AsyncGenerator

# 第三方库
import pytest
from httpx import ASGITransport, AsyncClient

# 本地模块
from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """全局事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """异步 HTTP 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
