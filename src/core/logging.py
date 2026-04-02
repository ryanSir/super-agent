"""结构化日志

格式：[模块] 描述 | key=value
遵循 CODING_STYLE_GUIDE.md 规范。
"""

# 标准库
import logging
import sys
from contextvars import ContextVar

# 请求级上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器

    输出格式：2024-01-01 12:00:00 [INFO] [request_id] message
    """

    def format(self, record: logging.LogRecord) -> str:
        request_id = request_id_var.get("")
        trace_id = trace_id_var.get("")

        # 构建前缀
        prefix_parts = []
        if request_id:
            prefix_parts.append(f"req={request_id[:8]}")
        if trace_id:
            prefix_parts.append(f"trace={trace_id[:8]}")

        prefix = f" [{' '.join(prefix_parts)}]" if prefix_parts else ""

        record.structured_prefix = prefix
        return super().format(record)


def setup_logging(level: str = "INFO") -> None:
    """初始化结构化日志"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        StructuredFormatter(
            fmt="%(asctime)s [%(levelname)s]%(structured_prefix)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # 降低第三方库日志级别
    for noisy in ("httpx", "httpcore", "uvicorn.access", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger

    Args:
        name: 模块名称，建议使用 __name__

    Returns:
        配置好的 Logger 实例

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info(f"[Orchestrator] 任务规划完成 | task_count=3 duration_ms=120")
    """
    return logging.getLogger(name)
