"""结构化 IPC 通信

解析 pi v0.62+ 的 JSONL 输出（--mode json），
将 assistant 消息、工具调用映射为 A2UI 事件。
"""

# 标准库
import json
from typing import List, Optional

# 本地模块
from src.core.logging import get_logger
from src.schemas.a2ui import A2UIEventType, ProcessUpdate, RenderWidget, TextStream
from src.schemas.sandbox import IPCMessage, PiAgentPhase

logger = get_logger(__name__)


def parse_jsonl(raw: str) -> List[IPCMessage]:
    """解析 pi --mode json 输出的 JSONL 内容，转换为 IPCMessage 列表

    pi v0.62+ 输出格式：每行一个 JSON 事件，type 字段区分类型。
    关键事件：
      - message_start/message_end: assistant 消息（含 tool_use / text）
      - agent_end: 包含完整 messages 列表，最后一条 assistant 消息即最终答案
    """
    messages = []
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]

    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            logger.warning(f"[IPC] JSONL 解析失败 | line={line[:100]} error={e}")
            continue

        event_type = data.get("type", "")

        if event_type == "agent_end":
            # 从最终消息列表中提取 final_answer
            for msg in reversed(data.get("messages", [])):
                if msg.get("role") == "assistant":
                    text = _extract_text(msg.get("content", []))
                    if text:
                        messages.append(IPCMessage(
                            phase=PiAgentPhase.FINAL_ANSWER,
                            content=text,
                        ))
                    break

        elif event_type == "message_start":
            msg = data.get("message", {})
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                # 工具调用
                for block in content:
                    if block.get("type") == "tool_use":
                        messages.append(IPCMessage(
                            phase=PiAgentPhase.ACTION,
                            tool_name=block.get("name", ""),
                            tool_input=block.get("input"),
                            content=f"调用工具: {block.get('name', '')}",
                        ))
                # 文本思考
                text = _extract_text(content)
                if text:
                    messages.append(IPCMessage(
                        phase=PiAgentPhase.THOUGHT,
                        content=text,
                    ))

        elif event_type == "tool_result":
            messages.append(IPCMessage(
                phase=PiAgentPhase.OBSERVATION,
                tool_output=str(data.get("content", "")),
                content=str(data.get("content", ""))[:200],
            ))

    return messages


def _extract_text(content: list) -> str:
    """从 content 块列表中提取纯文本"""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts).strip()


def extract_final_answer(raw: str) -> str:
    """从 pi JSONL 输出中直接提取最终答案文本"""
    for line in reversed(raw.strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "agent_end":
                for msg in reversed(data.get("messages", [])):
                    if msg.get("role") == "assistant":
                        text = _extract_text(msg.get("content", []))
                        if text:
                            return text
        except json.JSONDecodeError:
            continue
    return ""


def ipc_to_a2ui_events(
    messages: List[IPCMessage],
    trace_id: str = "",
) -> List[dict]:
    """将 IPC 消息转换为 A2UI 事件帧"""
    events = []

    for msg in messages:
        if msg.phase == PiAgentPhase.THOUGHT:
            event = ProcessUpdate(
                trace_id=trace_id,
                phase="thinking",
                status="in_progress",
                message=msg.content[:200],
            )
        elif msg.phase == PiAgentPhase.ACTION:
            event = ProcessUpdate(
                trace_id=trace_id,
                phase="executing",
                status="in_progress",
                message=f"执行工具: {msg.tool_name}",
                details={"tool_name": msg.tool_name, "tool_input": msg.tool_input},
            )
        elif msg.phase == PiAgentPhase.OBSERVATION:
            event = ProcessUpdate(
                trace_id=trace_id,
                phase="observing",
                status="in_progress",
                message=f"工具结果: {(msg.tool_output or '')[:100]}",
                details={"tool_output": msg.tool_output},
            )
        elif msg.phase == PiAgentPhase.FINAL_ANSWER:
            event = TextStream(
                trace_id=trace_id,
                delta=msg.content,
                is_final=True,
            )
        else:
            continue

        events.append(event.model_dump())

    return events


def get_new_messages(
    all_messages: List[IPCMessage],
    last_count: int,
) -> List[IPCMessage]:
    """获取增量 IPC 消息（用于轮询）"""
    return all_messages[last_count:]

