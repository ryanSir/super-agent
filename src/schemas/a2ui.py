"""A2UI (Agent-to-UI) 消息帧协议

Server-Driven UI 的智能体延伸版本。
后端 Agent 输出结构化 JSON 渲染指令，前端 Component Registry 动态组装。
"""

# 标准库
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

# 第三方库
from pydantic import BaseModel, Field


# ============================================================
# A2UI 事件类型
# ============================================================

class A2UIEventType(str, enum.Enum):
    """A2UI 事件类型"""
    RENDER_WIDGET = "render_widget"
    UPDATE_WIDGET = "update_widget"
    REMOVE_WIDGET = "remove_widget"
    PROCESS_UPDATE = "process_update"
    TEXT_STREAM = "text_stream"


# ============================================================
# A2UI 消息帧
# ============================================================

class A2UIFrame(BaseModel):
    """A2UI 消息帧基类

    所有 A2UI 消息都遵循此结构，通过 WebSocket 下发给前端。

    Example:
        >>> frame = RenderWidget(
        ...     trace_id="req-8899-abc",
        ...     ui_component="PatentTrendChart",
        ...     props={"title": "近三个月 AI 专利趋势", "xAxis": ["1月", "2月", "3月"]}
        ... )
    """
    trace_id: str = ""
    event_type: A2UIEventType
    timestamp: datetime = Field(default_factory=datetime.now)


class RenderWidget(A2UIFrame):
    """渲染组件指令 — 动态映射到前端具体组件"""
    event_type: A2UIEventType = A2UIEventType.RENDER_WIDGET
    widget_id: str = Field(default="", description="组件实例 ID，用于后续更新/移除")
    ui_component: str = Field(..., description="前端组件名称，映射到 ComponentRegistry")
    props: Dict[str, Any] = Field(default_factory=dict, description="组件 props")


class ProcessUpdate(A2UIFrame):
    """执行状态微件 — 进度条、终端日志等"""
    event_type: A2UIEventType = A2UIEventType.PROCESS_UPDATE
    phase: str = ""
    status: str = "in_progress"  # in_progress | completed | failed
    message: str = ""
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    details: Optional[Dict[str, Any]] = None


class DataChart(RenderWidget):
    """结构化数据图表 — ECharts 交互式展示"""
    ui_component: str = "DataChart"
    props: Dict[str, Any] = Field(
        default_factory=dict,
        description="ECharts 配置项：title, xAxis, yAxis, series 等",
    )


class ArtifactPreview(RenderWidget):
    """安全制品预览舱 — Sandboxed IFrame"""
    ui_component: str = "ArtifactPreview"
    props: Dict[str, Any] = Field(
        default_factory=dict,
        description="artifact_url, artifact_type (html/image/code), sandbox_config",
    )


class TextStream(A2UIFrame):
    """文本流式输出"""
    event_type: A2UIEventType = A2UIEventType.TEXT_STREAM
    delta: str = ""
    is_final: bool = False
