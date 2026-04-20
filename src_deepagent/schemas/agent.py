"""Agent 核心数据模型

定义 DAG 任务节点、执行拓扑、Agent 间通信消息等结构化契约。
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────────


class TaskType(str, enum.Enum):
    """任务类型"""

    WEB_SEARCH = "web_search"
    SANDBOX_CODING = "sandbox_coding"
    DATA_ANALYSIS = "data_analysis"
    SUB_AGENT_TASK = "sub_agent_task"


class RiskLevel(str, enum.Enum):
    """任务风险等级 — 决定路由到可信 Worker 还是沙箱 Worker"""

    SAFE = "safe"
    DANGEROUS = "dangerous"


class TaskStatus(str, enum.Enum):
    """任务执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SessionStatus(str, enum.Enum):
    """会话状态机"""

    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# ── DAG 任务模型 ──────────────────────────────────────────


class TaskNode(BaseModel):
    """DAG 中的单个任务节点"""

    task_id: str = Field(description="任务唯一标识")
    task_type: TaskType = Field(description="任务类型")
    risk_level: RiskLevel = Field(default=RiskLevel.SAFE, description="风险等级")
    description: str = Field(default="", description="任务描述（供 LLM 理解）")
    input_data: dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    depends_on: list[str] = Field(default_factory=list, description="依赖的前置任务 ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="执行状态")


class ExecutionDAG(BaseModel):
    """任务执行拓扑（有向无环图）"""

    dag_id: str = Field(description="DAG 唯一标识")
    query: str = Field(description="原始用户查询")
    tasks: list[TaskNode] = Field(default_factory=list, description="任务节点列表")
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def task_map(self) -> dict[str, TaskNode]:
        """按 task_id 索引"""
        return {t.task_id: t for t in self.tasks}

    @property
    def root_tasks(self) -> list[TaskNode]:
        """无依赖的根任务"""
        return [t for t in self.tasks if not t.depends_on]


# ── Agent 通信消息 ────────────────────────────────────────


class AgentMessage(BaseModel):
    """Agent 间通信消息"""

    role: str = Field(description="消息角色: orchestrator / worker / sandbox / system")
    content: str = Field(description="消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class PlanResult(BaseModel):
    """Orchestrator 规划结果"""

    dag: ExecutionDAG
    reasoning: str = Field(default="", description="规划推理过程")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="规划置信度")


class WorkerResult(BaseModel):
    """Worker 执行结果"""

    task_id: str = Field(description="任务 ID")
    success: bool = Field(description="是否成功")
    data: Any = Field(default=None, description="执行结果数据")
    error: str = Field(default="", description="错误信息")
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorOutput(BaseModel):
    """编排器最终输出 — PydanticAI result_type"""

    answer: str = Field(default="", description="最终回答")
    plan: PlanResult | None = Field(default=None, description="执行计划")
    worker_results: list[WorkerResult] = Field(default_factory=list, description="Worker 结果")
    sub_agent_results: list[dict[str, Any]] = Field(
        default_factory=list, description="Sub-Agent 执行结果"
    )
    a2ui_frames: list[dict[str, Any]] = Field(default_factory=list, description="A2UI 渲染帧")
    trace_id: str = Field(default="", description="追踪 ID")
