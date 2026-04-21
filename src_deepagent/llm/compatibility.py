"""模型协议兼容层。"""

from __future__ import annotations

from typing import Any

from src_deepagent.orchestrator.reasoning_engine import ExecutionMode
from src_deepagent.llm.schemas import ModelProfile


def patch_messages_for_model(messages: list[dict[str, Any]], profile: ModelProfile) -> list[dict[str, Any]]:
    """按模型能力补丁消息。

    当前 Phase 1 只预留扩展点，后续在此处理 reasoning_content/tool-call 协议差异。
    """
    return messages


def should_inject_reasoning_content(profile: ModelProfile) -> bool:
    """判断是否需要对 tool-call 消息补 reasoning_content。"""
    return profile.capabilities.requires_reasoning_content_on_tool_call


def max_tokens_for_execution_mode(execution_mode: str) -> int:
    """按执行模式返回统一的 max_tokens。"""
    return {
        ExecutionMode.DIRECT.value: 4000,
        ExecutionMode.AUTO.value: 8000,
        ExecutionMode.PLAN_AND_EXECUTE.value: 16000,
        ExecutionMode.SUB_AGENT.value: 16000,
    }.get(execution_mode, 8000)


def thinking_level_for_execution_mode(execution_mode: str) -> str:
    """按执行模式返回统一 thinking level。

    - direct: low，优先响应速度
    - auto: medium，平衡成本与效果
    - plan/sub_agent: high，优先推理质量
    """
    return {
        ExecutionMode.DIRECT.value: "low",
        ExecutionMode.AUTO.value: "medium",
        ExecutionMode.PLAN_AND_EXECUTE.value: "high",
        ExecutionMode.SUB_AGENT.value: "high",
    }.get(execution_mode, "medium")
