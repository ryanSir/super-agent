"""Provider adapter 基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src_deepagent.llm.schemas import ModelProfile, ProviderConfig


class BaseProvider(ABC):
    """Provider adapter 抽象。"""

    @abstractmethod
    def create_model(self, profile: ModelProfile, provider_cfg: ProviderConfig) -> Any:
        """创建模型实例。"""

    @abstractmethod
    def create_model_settings(self, profile: ModelProfile, execution_mode: str) -> Any | None:
        """创建运行时模型设置。"""
