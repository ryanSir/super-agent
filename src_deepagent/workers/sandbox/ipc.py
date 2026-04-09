"""Pi Agent JSONL 输出解析

解析 Pi Agent 在沙箱内产生的 JSONL 格式输出。
"""

from __future__ import annotations

import json
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


class PiAgentEvent:
    """Pi Agent 输出事件"""

    __slots__ = ("event_type", "data")

    def __init__(self, event_type: str, data: dict[str, Any]) -> None:
        self.event_type = event_type
        self.data = data

    def __repr__(self) -> str:
        return f"PiAgentEvent(type={self.event_type})"


def parse_jsonl_output(raw_output: str) -> list[PiAgentEvent]:
    """解析 Pi Agent 的 JSONL 输出

    Args:
        raw_output: Pi Agent 的标准输出（每行一个 JSON 对象）

    Returns:
        解析后的事件列表
    """
    events: list[PiAgentEvent] = []
    for line_num, line in enumerate(raw_output.strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            event_type = obj.get("type", "unknown")
            events.append(PiAgentEvent(event_type=event_type, data=obj))
        except json.JSONDecodeError as e:
            logger.warning(f"JSONL 解析失败 | line={line_num} error={e} content={line[:200]}")
    return events


def extract_final_answer(events: list[PiAgentEvent]) -> str:
    """从事件列表中提取最终回答

    适配 Pi v3 JSONL 格式：
    - agent_end 事件包含完整的 messages 列表
    - turn_end / message_end 事件包含单条消息
    - message_update(text_end) 包含文本片段
    """
    # 优先从 agent_end 提取（包含完整对话）
    for event in reversed(events):
        if event.event_type == "agent_end":
            messages = event.data.get("messages", [])
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", [])
                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    if texts:
                        return "\n".join(texts)

    # fallback: 从 turn_end / message_end 提取
    for event in reversed(events):
        if event.event_type in ("turn_end", "message_end"):
            msg = event.data.get("message", {})
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if texts:
                    return "\n".join(texts)

    # fallback: 从 message_update(text_end) 提取
    for event in reversed(events):
        if event.event_type == "message_update":
            assistant_event = event.data.get("assistantMessageEvent", {})
            if assistant_event.get("type") == "text_end":
                return assistant_event.get("content", "")

    return ""


def extract_artifacts(events: list[PiAgentEvent]) -> list[dict[str, Any]]:
    """从事件列表中提取产物信息"""
    artifacts: list[dict[str, Any]] = []
    for event in events:
        if event.event_type == "artifact":
            artifacts.append(event.data)
        # Pi v3: tool_result 中可能包含文件产物
        elif event.event_type == "tool_result":
            result = event.data.get("result", {})
            if isinstance(result, dict) and result.get("type") == "file":
                artifacts.append(result)
    return artifacts
