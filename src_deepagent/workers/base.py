"""Worker 协议与基类

定义 WorkerProtocol 统一接口和 BaseWorker 模板方法。
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Protocol, runtime_checkable

from src_deepagent.core.exceptions import WorkerError
from src_deepagent.core.logging import get_logger
from src_deepagent.schemas.agent import TaskNode, WorkerResult

logger = get_logger(__name__)


@runtime_checkable
class WorkerProtocol(Protocol):
    """Worker 统一接口"""

    @property
    def name(self) -> str: ...

    async def execute(self, task: TaskNode) -> WorkerResult: ...


class BaseWorker:
    """Worker 基类 — 模板方法模式

    子类实现 _do_execute()，基类负责日志、追踪、异常处理。
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    async def execute(self, task: TaskNode) -> WorkerResult:
        """执行入口（模板方法）"""
        start = time.monotonic()
        logger.info(
            f"[{self.name}] 开始执行 | task_id={task.task_id} "
            f"task_type={task.task_type.value}"
        )
        try:
            result = await self._do_execute(task)
            elapsed = time.monotonic() - start
            logger.info(
                f"[{self.name}] 执行完成 | task_id={task.task_id} "
                f"success={result.success} elapsed={elapsed:.2f}s"
            )
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                f"[{self.name}] 执行失败 | task_id={task.task_id} "
                f"error={e} elapsed={elapsed:.2f}s"
            )
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                metadata={"worker": self.name, "elapsed": elapsed},
            )

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """子类实现具体执行逻辑"""
        raise NotImplementedError
