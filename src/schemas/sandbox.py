"""沙箱 IPC 消息契约

定义 Python 宿主与 E2B 沙箱之间的结构化通信协议。
基于 .pi_state.jsonl 文件的跨进程通信。
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

class SandboxStatus(str, enum.Enum):
    """沙箱生命周期状态"""
    CREATING = "creating"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    DESTROYED = "destroyed"


class PiAgentPhase(str, enum.Enum):
    """Pi Agent ReAct 循环阶段"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    FINAL_ANSWER = "final_answer"


# ============================================================
# 沙箱任务模型
# ============================================================

class SandboxTask(BaseModel):
    """沙箱任务描述 — Python 宿主下发给沙箱的任务

    Args:
        task_id: 任务 ID（与 DAG TaskNode 对应）
        instruction: 自然语言任务指令
        context_files: 需要注入沙箱的文件（路径 → 内容）
        env_vars: 注入沙箱的环境变量
        timeout: 执行超时（秒）
    """
    task_id: str
    instruction: str
    context_files: Dict[str, str] = Field(default_factory=dict)
    env_vars: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=300, ge=30, le=1800)


# ============================================================
# IPC 通信消息
# ============================================================

class IPCMessage(BaseModel):
    """IPC 通信消息 — .pi_state.jsonl 中的单行记录

    Pi Agent 在沙箱内将状态追加到 .pi_state.jsonl，
    Python 宿主通过 files.watch 轮询读取。
    """
    phase: PiAgentPhase
    content: str = ""
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SandboxState(BaseModel):
    """沙箱实时状态"""
    sandbox_id: str
    status: SandboxStatus
    current_phase: Optional[PiAgentPhase] = None
    iteration: int = 0
    max_iterations: int = 10
    messages: List[IPCMessage] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


# ============================================================
# 沙箱执行结果
# ============================================================

class Artifact(BaseModel):
    """沙箱产物"""
    filename: str
    content_type: str  # "text/html", "image/png", "text/python", etc.
    content: Optional[str] = None  # 文本内容
    binary_url: Optional[str] = None  # 二进制文件 URL
    size_bytes: int = 0


class SandboxResult(BaseModel):
    """沙箱执行结果 — 沙箱 Worker 回传给 Orchestrator"""
    task_id: str
    sandbox_id: str
    success: bool
    final_answer: str = ""
    artifacts: List[Artifact] = Field(default_factory=list)
    iterations_used: int = 0
    error: str = ""
    ipc_log: List[IPCMessage] = Field(default_factory=list)
