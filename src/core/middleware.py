"""FastAPI 中间件

- RequestID 中间件：为每个请求生成唯一 ID
- 全局异常处理：将 AgentBaseError 映射为标准 HTTP 响应
"""

# 标准库
import time
import uuid

# 第三方库
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 本地模块
from src.core.exceptions import AgentBaseError
from src.core.logging import get_logger, request_id_var, trace_id_var

logger = get_logger(__name__)


def register_middleware(app: FastAPI) -> None:
    """注册所有中间件"""
    _register_cors(app)
    _register_request_id(app)
    _register_exception_handlers(app)


def _register_cors(app: FastAPI) -> None:
    """CORS 中间件"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_request_id(app: FastAPI) -> None:
    """RequestID + Trace 中间件"""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # 优先从 header 获取，支持链路透传
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        trace_id = request.headers.get("X-Trace-ID", req_id)

        request_id_var.set(req_id)
        trace_id_var.set(trace_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Trace-ID"] = trace_id

        logger.info(
            f"[Gateway] {request.method} {request.url.path} | "
            f"status={response.status_code} duration_ms={duration_ms}"
        )
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    """全局异常处理"""

    @app.exception_handler(AgentBaseError)
    async def agent_error_handler(request: Request, exc: AgentBaseError):
        """将 AgentBaseError 映射为标准 HTTP 响应"""
        from src.core.exceptions import (
            LLMRateLimitError,
            OrchestrationTimeout,
            SandboxTimeoutError,
        )

        # 根据异常类型映射 HTTP 状态码
        status_map = {
            LLMRateLimitError: 429,
            OrchestrationTimeout: 504,
            SandboxTimeoutError: 504,
        }
        status_code = status_map.get(type(exc), 500)

        logger.error(
            f"[ExceptionHandler] {type(exc).__name__} | "
            f"trace_id={exc.trace_id} message={exc.message}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": exc.to_dict(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        """兜底：未预期的异常"""
        logger.error(
            f"[ExceptionHandler] 未处理异常 | "
            f"error_type={type(exc).__name__} message={str(exc)}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "error_type": "InternalServerError",
                    "message": "服务内部错误",
                },
            },
        )
