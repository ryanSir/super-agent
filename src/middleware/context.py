"""Middleware 上下文

贯穿整个请求生命周期，在 middleware 间共享状态。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TokenUsage:
    """累计 token 使用量"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class MiddlewareContext:
    """中间件上下文

    在 pipeline 入口创建，贯穿所有 middleware 的钩子调用。
    """
    session_id: str
    trace_id: str
    messages: List[Any] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    metadata: Dict[str, Any] = field(default_factory=dict)
