"""业务异常层级

所有业务异常继承自 AgentError 基类，禁止裸抛 Exception。
"""

from __future__ import annotations


class AgentError(Exception):
    """Agent 系统异常基类"""

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


# ── 推理引擎 ──────────────────────────────────────────────


class ReasoningError(AgentError):
    """推理引擎错误（复杂度评估/模式决策/资源获取）"""


# ── Sub-Agent ─────────────────────────────────────────────


class SubAgentError(AgentError):
    """Sub-Agent 执行错误"""


class SubAgentTimeoutError(SubAgentError):
    """Sub-Agent 执行超时"""


# ── Worker ────────────────────────────────────────────────


class WorkerError(AgentError):
    """Worker 执行错误"""


class RoutingError(WorkerError):
    """任务路由错误（未找到匹配的 Worker）"""


# ── 桥接层 ────────────────────────────────────────────────


class BridgeError(AgentError):
    """桥接工具错误（Worker/Skill 调用失败）"""


# ── 沙箱 ──────────────────────────────────────────────────


class SandboxError(AgentError):
    """沙箱相关错误"""


class SandboxTimeoutError(SandboxError):
    """沙箱执行超时"""


class SandboxExecutionError(SandboxError):
    """沙箱内代码执行失败"""


# ── LLM ───────────────────────────────────────────────────


class LLMError(AgentError):
    """LLM 调用错误"""


class LLMRateLimitError(LLMError):
    """LLM API 速率限制"""


class LLMTokenExceededError(LLMError):
    """Token 超出限制"""


# ── 规划 ──────────────────────────────────────────────────


class PlanningError(AgentError):
    """任务规划错误（DAG 生成失败）"""


# ── 记忆 ──────────────────────────────────────────────────


class MemoryError(AgentError):
    """记忆系统错误"""
