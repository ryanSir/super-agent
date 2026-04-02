"""FastAPI 应用入口

企业级混合智能体核心引擎
"""

# 标准库
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

# 第三方库
from fastapi import FastAPI

# 本地模块
from src.config.settings import get_settings
from src.core.dependencies import close_redis
from src.core.logging import get_logger, setup_logging
from src.core.middleware import register_middleware
from src.gateway.router import register_routes
from src.llm.config import setup_litellm
from src.monitoring.otel_setup import setup_otel
from src.skills.registry import skill_registry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.app.app_debug else "INFO")

    logger.info(
        f"[App] 启动 super-agent 核心引擎 | "
        f"env={settings.app.app_env} port={settings.app.app_port}"
    )

    # 启动 Temporal Worker（失败时降级，不阻塞应用启动）
    temporal_task: Optional[asyncio.Task] = None
    try:
        from src.state.temporal_worker import start_temporal_worker
        worker = await start_temporal_worker()
        temporal_task = asyncio.create_task(worker.run())
    except Exception as e:
        logger.warning(f"[App] Temporal Worker 启动失败，将降级为直接执行 | error={e}")

    yield

    # 停止 Temporal Worker
    if temporal_task and not temporal_task.done():
        temporal_task.cancel()
        try:
            await temporal_task
        except asyncio.CancelledError:
            pass

    # 清理资源
    await close_redis()
    logger.info("[App] 核心引擎已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title="Super Agent 核心引擎",
        description="企业级混合智能体 - Python 宏观编排 + TS 沙箱微观执行",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app.app_debug else None,
        redoc_url="/redoc" if settings.app.app_debug else None,
    )

    register_middleware(app)
    register_routes(app)
    setup_litellm()
    setup_otel()

    # 扫描注册 skills
    skill_count = skill_registry.scan()
    logger.info(f"[App] Skills 注册完成 | count={skill_count}")

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "super-agent", "env": settings.app.app_env}

    return app


app = create_app()
