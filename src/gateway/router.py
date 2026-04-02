"""路由聚合

挂载 REST + WebSocket 路由到 FastAPI 应用。
"""

# 第三方库
from fastapi import FastAPI

# 本地模块
from src.gateway.rest_api import router as rest_router
from src.gateway.websocket_api import router as ws_router


def register_routes(app: FastAPI) -> None:
    """注册所有路由

    Args:
        app: FastAPI 应用实例
    """
    app.include_router(rest_router, prefix="/api/agent", tags=["Agent"])
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
