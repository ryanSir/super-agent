"""模型协议兼容层占位。"""

from __future__ import annotations

from typing import Any

from src_deepagent.llm.schemas import ModelProfile


def patch_messages_for_model(messages: list[dict[str, Any]], profile: ModelProfile) -> list[dict[str, Any]]:
    """按模型能力补丁消息。

    当前 Phase 1 只预留扩展点，后续在此处理 reasoning_content/tool-call 协议差异。
    """
    return messages


def should_inject_reasoning_content(profile: ModelProfile) -> bool:
    """判断是否需要对 tool-call 消息补 reasoning_content。"""
    return profile.capabilities.requires_reasoning_content_on_tool_call
