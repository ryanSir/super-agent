# A2UI 协议规格

## 概念

A2UI（Agent-to-UI）是 Server-Driven UI 的智能体延伸版本。
后端 Agent 输出结构化 JSON 渲染指令，前端 ComponentRegistry 动态组装 UI。

## 核心文件

- `src/schemas/a2ui.py` — 消息帧数据模型
- `frontend/src/engine/ComponentRegistry.tsx` — 前端组件注册表
- `frontend/src/engine/MessageHandler.ts` — 事件处理状态机

## 消息帧层级

```
A2UIFrame (基类)
├── RenderWidget       — 渲染组件指令
│   ├── DataChart      — ECharts 图表（继承 RenderWidget）
│   └── ArtifactPreview — 安全制品预览（Sandboxed IFrame）
├── ProcessUpdate      — 执行状态（进度条、终端日志）
└── TextStream         — 文本流式输出
```

## 消息帧定义

### 基类

```python
class A2UIFrame(BaseModel):
    trace_id: str = ""
    event_type: A2UIEventType
    timestamp: datetime
```

### RenderWidget（渲染组件）

```python
class RenderWidget(A2UIFrame):
    event_type = "render_widget"
    widget_id: str          # 组件实例 ID，用于后续 update/remove
    ui_component: str       # 前端组件名，映射到 ComponentRegistry
    props: Dict[str, Any]   # 组件 props
```

### DataChart（图表）

```python
class DataChart(RenderWidget):
    ui_component = "DataChart"
    props: {
        "title": str,
        "chartType": "line" | "bar" | "pie" | "scatter",
        "xAxis": List[str],
        "seriesData": List[number] | List[{"name": str, "data": List[number]}]
    }
```

### ArtifactPreview（制品预览）

```python
class ArtifactPreview(RenderWidget):
    ui_component = "ArtifactPreview"
    props: {
        "artifact_url": str,
        "artifact_type": "html" | "image" | "code",
        "sandbox_config": dict
    }
```

### ProcessUpdate（进度）

```python
class ProcessUpdate(A2UIFrame):
    event_type = "process_update"
    phase: str
    status: "in_progress" | "completed" | "failed"
    message: str
    progress: Optional[float]  # 0.0 ~ 1.0
    details: Optional[Dict]
```

### TextStream（文本流）

```python
class TextStream(A2UIFrame):
    event_type = "text_stream"
    delta: str      # 增量文本片段
    is_final: bool  # true 表示流结束
```

## 事件类型枚举

```python
class A2UIEventType(str, Enum):
    RENDER_WIDGET  = "render_widget"
    UPDATE_WIDGET  = "update_widget"
    REMOVE_WIDGET  = "remove_widget"
    PROCESS_UPDATE = "process_update"
    TEXT_STREAM    = "text_stream"
```

## 前端支持的组件

| ui_component | 组件文件 | 用途 |
|-------------|---------|------|
| `DataChart` | `DataWidget.tsx` | ECharts 交互图表 |
| `ArtifactPreview` | `ArtifactPreview.tsx` | 代码/HTML/图片预览 |
| `TerminalView` | `TerminalView.tsx` | xterm 终端模拟 |
| `ProcessUI` | `StepsTimeline.tsx` | 步骤时间线 |

## 关键约束

- `widget_id` 全局唯一，格式为 `chart-{uuid8}` 或 `widget-{uuid8}`
- Orchestrator 通过 `emit_chart` / `emit_widget` tool 生成渲染帧
- 渲染帧同时写入 `deps.a2ui_frames`（内存）和 Redis Stream（实时推送）
- 前端 ComponentRegistry 按 `ui_component` 字段动态映射，未知组件名会被忽略
- 新增前端组件必须同步在 ComponentRegistry 中注册
