"""沙箱数据模型

定义沙箱任务、执行结果和产物。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SandboxTask(BaseModel):
    """沙箱执行任务"""

    task_id: str = Field(description="任务 ID")
    instruction: str = Field(description="执行指令")
    context_files: dict[str, str] = Field(
        default_factory=dict, description="注入沙箱的文件（路径→内容）"
    )
    timeout: int = Field(default=120, description="超时秒数")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """沙箱产物"""

    name: str = Field(description="文件名")
    path: str = Field(description="沙箱内路径")
    content_type: str = Field(default="application/octet-stream", description="MIME 类型")
    size: int = Field(default=0, description="文件大小（字节）")
    created_at: datetime = Field(default_factory=datetime.now)


class SandboxResult(BaseModel):
    """沙箱执行结果"""

    task_id: str = Field(description="任务 ID")
    success: bool = Field(description="是否成功")
    stdout: str = Field(default="", description="标准输出")
    stderr: str = Field(default="", description="标准错误")
    exit_code: int = Field(default=0, description="退出码")
    artifacts: list[Artifact] = Field(default_factory=list, description="产物列表")
    error: str = Field(default="", description="错误信息")
    metadata: dict[str, Any] = Field(default_factory=dict)
