"""A2UI 事件帧数据模型

定义 Agent-to-UI 协议的事件帧结构，所有 SSE 事件遵循统一信封格式。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class A2UIFrame(BaseModel):
    """A2UI 事件帧基类"""

    event_type: str = Field(description="事件类型")
    trace_id: str = Field(default="", description="追踪 ID")
    session_id: str = Field(default="", description="会话 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")

    def to_event_dict(self) -> dict[str, Any]:
        """输出标准 JSON dict，datetime 转 ISO 格式"""
        d = self.model_dump()
        d["timestamp"] = self.timestamp.isoformat()
        return d


class TextStreamFrame(A2UIFrame):
    """LLM 文本流式输出"""

    event_type: str = "text_stream"
    delta: str = Field(default="", description="增量文本片段")
    is_final: bool = Field(default=False, description="是否为最后一帧")


class RenderWidgetFrame(A2UIFrame):
    """渲染组件指令"""

    event_type: str = "render_widget"
    widget_id: str = Field(default_factory=lambda: f"widget-{uuid.uuid4().hex[:8]}")
    ui_component: str = Field(description="前端组件名")
    props: dict[str, Any] = Field(default_factory=dict, description="组件 props")


class ToolResultFrame(A2UIFrame):
    """工具执行结果"""

    event_type: str = "tool_result"
    tool_name: str = Field(description="工具名称")
    tool_type: str = Field(default="tool", description="工具类型")
    status: str = Field(default="success", description="执行状态")
    content: str = Field(default="", description="结果摘要")


class ProcessUpdateFrame(A2UIFrame):
    """执行进度更新"""

    event_type: str = "process_update"
    phase: str = Field(description="当前阶段")
    status: str = Field(default="in_progress", description="阶段状态")
    message: str = Field(default="", description="进度消息")
    progress: float | None = Field(default=None, description="进度百分比 0.0~1.0")
