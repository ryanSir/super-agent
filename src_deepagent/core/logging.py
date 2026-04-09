"""结构化日志

所有日志条目携带 trace_id 和 session_id，格式：[session_id][trace_id] message
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

# ── 上下文变量 ────────────────────────────────────────────

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


# ── 自定义 Formatter ──────────────────────────────────────


class StructuredFormatter(logging.Formatter):
    """注入 session_id / trace_id 的结构化日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        sid = session_id_var.get("")
        tid = trace_id_var.get("")
        prefix = ""
        if sid:
            prefix += f"[{sid}]"
        if tid:
            prefix += f"[{tid}]"
        if prefix:
            record.msg = f"{prefix} {record.msg}"
        return super().format(record)


# ── 日志工厂 ──────────────────────────────────────────────

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_initialized = False


def _ensure_init() -> None:
    """确保根日志只初始化一次"""
    global _initialized  # noqa: PLW0603
    if _initialized:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取带结构化格式的 logger"""
    _ensure_init()
    return logging.getLogger(name)
