"""记忆数据模型"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户画像"""
    work_context: str = ""
    personal_context: str = ""
    top_of_mind: str = ""


class Fact(BaseModel):
    """事实记录"""
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    source_session_id: str = ""


class MemoryData(BaseModel):
    """完整记忆结构"""
    profile: UserProfile = Field(default_factory=UserProfile)
    facts: List[Fact] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
