"""Agent 核心数据模型

定义 DAG 任务节点、执行拓扑、Agent 间通信消息等结构化契约。
"""

# 标准库
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

# 第三方库
from pydantic import BaseModel, Field


# ============================================================
# 枚举定义
# ============================================================

class TaskType(str, enum.Enum):
    """任务类型"""
    RAG_RETRIEVAL = "rag_retrieval"
    DB_QUERY = "db_query"
    API_CALL = "api_call"
    SANDBOX_CODING = "sandbox_coding"
    DATA_ANALYSIS = "data_analysis"


class RiskLevel(str, enum.Enum):
    """任务风险等级 — 决定路由到可信 Worker 还是沙箱 Worker"""
    SAFE = "safe"          # 可信 Worker（Python 原生）
    DANGEROUS = "dangerous"  # 沙箱 Worker（TS 隔离）


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


# ============================================================
# DAG 任务模型
# ============================================================

class TaskNode(BaseModel):
    """DAG 中的单个任务节点

    Args:
        task_id: 任务唯一标识
        task_type: 任务类型
        risk_level: 风险等级，决定路由策略
        description: 任务描述（供 LLM 理解）
        input_data: 任务输入数据
        depends_on: 依赖的前置任务 ID 列表
    """
    task_id: str
    task_type: TaskType
    risk_level: RiskLevel = RiskLevel.SAFE
    description: str = ""
    input_data: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


class ExecutionDAG(BaseModel):
    """任务执行拓扑（有向无环图）

    Orchestrator 规划的全局执行计划。
    """
    dag_id: str
    query: str
    tasks: List[TaskNode]
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def task_map(self) -> Dict[str, TaskNode]:
        """按 task_id 索引"""
        return {t.task_id: t for t in self.tasks}

    @property
    def root_tasks(self) -> List[TaskNode]:
        """无依赖的根任务"""
        return [t for t in self.tasks if not t.depends_on]


# ============================================================
# Agent 通信消息
# ============================================================

class AgentMessage(BaseModel):
    """Agent 间通信消息"""
    role: str  # "orchestrator" | "worker" | "sandbox" | "system"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class PlanResult(BaseModel):
    """Orchestrator 规划结果"""
    dag: ExecutionDAG
    reasoning: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class WorkerResult(BaseModel):
    """Worker 执行结果"""
    task_id: str
    success: bool
    data: Any = None
    error: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestratorOutput(BaseModel):
    """编排器最终输出 — PydanticAI result_type"""
    answer: str = ""
    plan: Optional[PlanResult] = None
    worker_results: List[WorkerResult] = Field(default_factory=list)
    a2ui_frames: List[Dict[str, Any]] = Field(default_factory=list)
    trace_id: str = ""
