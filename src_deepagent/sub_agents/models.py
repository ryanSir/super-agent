"""Sub-Agent 输入输出契约

自包含的数据模型，不依赖主 Agent 内部状态。
未来升级 multi-agent 时 Sub-Agent 本身不需要改。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SubAgentInput(BaseModel):
    """Sub-Agent 接收的任务输入"""

    task_id: str = Field(description="任务 ID")
    sub_agent_name: str = Field(description="Sub-Agent 角色名: researcher / analyst / writer")
    instruction: str = Field(description="任务指令")
    context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")
    parent_results: dict[str, Any] = Field(
        default_factory=dict, description="前置任务结果（task_id → result）"
    )
    timeout: int = Field(default=120, description="超时秒数")


class SubAgentOutput(BaseModel):
    """Sub-Agent 的执行输出"""

    task_id: str = Field(description="任务 ID")
    success: bool = Field(description="是否成功")
    answer: str = Field(default="", description="执行结果摘要")
    data: Any = Field(default=None, description="结构化结果数据")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="产物列表")
    token_usage: dict[str, int] = Field(default_factory=dict, description="Token 用量")
    error: str = Field(default="", description="错误信息")
