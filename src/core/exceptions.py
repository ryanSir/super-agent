"""智能体异常体系

按错误域分层：编排层 → Worker 层 → 沙箱层 → LLM 层
所有异常携带 trace_id + 结构化上下文，中间件统一映射为 HTTP 响应。
"""

# 标准库
from typing import Any, Dict, Optional


# ============================================================
# 基类
# ============================================================

class AgentBaseError(Exception):
    """所有智能体异常的基类

    Args:
        message: 错误描述
        trace_id: 全链路追踪 ID
        context: 结构化上下文信息
    """

    def __init__(
        self,
        message: str,
        *,
        trace_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.trace_id = trace_id
        self.context = context or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典"""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "trace_id": self.trace_id,
            "context": self.context,
        }


# ============================================================
# 编排层异常
# ============================================================

class PlanningError(AgentBaseError):
    """DAG 规划失败（意图无法拆解）"""


class RoutingError(AgentBaseError):
    """任务路由失败（无匹配 Worker）"""


class OrchestrationTimeout(AgentBaseError):
    """编排超时"""


# ============================================================
# Worker 层异常
# ============================================================

class WorkerError(AgentBaseError):
    """Worker 执行失败基类"""


class RAGRetrievalError(WorkerError):
    """RAG 检索失败"""


class APICallError(WorkerError):
    """内部 API 调用失败"""


# ============================================================
# 沙箱层异常
# ============================================================

class SandboxError(AgentBaseError):
    """沙箱异常基类"""


class SandboxCreationError(SandboxError):
    """沙箱创建失败"""


class SandboxExecutionError(SandboxError):
    """沙箱内代码执行失败"""


class SandboxTimeoutError(SandboxError):
    """沙箱执行超时"""


class IPCError(SandboxError):
    """IPC 通信异常"""


# ============================================================
# LLM 层异常
# ============================================================

class LLMError(AgentBaseError):
    """LLM 调用异常基类"""


class LLMRateLimitError(LLMError):
    """限流"""


class LLMTokenExceededError(LLMError):
    """Token 超限"""


class LLMResponseValidationError(LLMError):
    """结构化输出校验失败"""
