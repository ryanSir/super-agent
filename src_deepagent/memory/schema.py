"""记忆数据模型"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户画像"""

    work_context: str = Field(default="", description="工作上下文")
    personal_context: str = Field(default="", description="个人偏好")
    top_of_mind: str = Field(default="", description="当前关注点")


class Fact(BaseModel):
    """记忆事实"""

    content: str = Field(description="事实内容")
    created_at: datetime = Field(default_factory=datetime.now)
    source_session_id: str = Field(default="", description="来源会话 ID")


class MemoryData(BaseModel):
    """用户完整记忆"""

    user_id: str = Field(description="用户 ID")
    profile: UserProfile = Field(default_factory=UserProfile)
    facts: list[Fact] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)
