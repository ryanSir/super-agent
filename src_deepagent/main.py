"""FastAPI 应用入口

应用工厂 + lifespan（启动时初始化 Redis/Workers/SkillRegistry，关闭时清理）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.gateway import rest_api, websocket_api
from src_deepagent.llm.config import configure_litellm
from src_deepagent.monitoring.langfuse_tracer import configure_langfuse, shutdown as langfuse_shutdown
from src_deepagent.capabilities.skills.registry import skill_registry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    settings = get_settings()
    logger.info(f"应用启动 | app={settings.app_name} debug={settings.debug}")

    # 初始化 LiteLLM
    configure_litellm()

    # 初始化 Langfuse 追踪
    configure_langfuse()

    # 初始化 Redis
    redis_client = await _init_redis(settings)

    # 初始化 Workers
    workers = rest_api.init_workers()

    # 扫描 Skills
    skill_count = skill_registry.scan(settings.skill_dir)
    logger.info(f"Skill 扫描完成 | count={skill_count}")

    # 配置网关
    rest_api.configure(workers=workers, redis_client=redis_client)

    # 启动预热：MCP 连接 + 定期刷新任务
    await rest_api.startup()

    logger.info("应用初始化完成")

    yield

    # 清理
    await rest_api.shutdown()
    langfuse_shutdown()
    if redis_client:
        await redis_client.close()
    logger.info("应用关闭")


async def _init_redis(settings) -> object | None:
    """初始化 Redis 客户端"""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis.url,
            decode_responses=True,
        )
        await client.ping()
        logger.info(f"Redis 连接成功 | url={settings.redis.host}:{settings.redis.port}")
        return client
    except Exception as e:
        logger.warning(f"Redis 连接失败，降级运行 | error={e}")
        return None


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="企业级智能体运行时 — 基于 pydantic-deepagents",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(rest_api.router)
    app.include_router(websocket_api.router)

    return app


# 应用实例
app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src_deepagent.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
