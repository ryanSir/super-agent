"""Worker Protocol 接口与基类

定义所有 Worker 的统一接口契约和公共逻辑。
"""

# 标准库
from typing import Any, Dict, Protocol, runtime_checkable

# 本地模块
from src.core.exceptions import WorkerError
from src.core.logging import get_logger
from src.monitoring.langfuse_tracer import get_langfuse, observation_span, trace_context
from src.monitoring.pipeline_events import pipeline_step
from src.monitoring.trace_context import get_trace_id
from src.schemas.agent import TaskNode, WorkerResult

logger = get_logger(__name__)


@runtime_checkable
class WorkerProtocol(Protocol):
    """Worker 统一接口"""

    @property
    def name(self) -> str: ...

    async def execute(self, task: TaskNode) -> WorkerResult: ...


class BaseWorker:
    """Worker 基类

    提供公共逻辑：结构化日志、Langfuse span、异常处理。
    子类只需实现 _do_execute 即可。
    """

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, task: TaskNode) -> WorkerResult:
        """执行任务（模板方法）

        Args:
            task: 任务节点

        Returns:
            WorkerResult: 执行结果
        """
        trace_id = get_trace_id()
        langfuse = get_langfuse()

        logger.info(
            f"[{self._name}] 开始执行 | "
            f"task_id={task.task_id} task_type={task.task_type}"
        )

        # Langfuse span 包裹
        trace = None
        if langfuse:
            try:
                trace = langfuse.trace(id=trace_id, name=f"worker:{self._name}")
            except Exception:
                pass

        try:
            async with pipeline_step(f"worker.native.{self._name}", metadata={
                "worker_type": self._name, "task_id": task.task_id,
            }) as ev:
                with observation_span(trace, name=f"{self._name}.execute"):
                    result = await self._do_execute(task)
                ev.add_metadata(success=result.success)

            logger.info(
                f"[{self._name}] 执行完成 | "
                f"task_id={task.task_id} success={result.success}"
            )
            return result

        except WorkerError:
            raise
        except Exception as e:
            logger.error(
                f"[{self._name}] 执行失败 | "
                f"task_id={task.task_id} error_type={type(e).__name__} error={e}",
                exc_info=True,
            )
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                metadata={"worker": self._name},
            )

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """子类实现具体执行逻辑

        Args:
            task: 任务节点

        Returns:
            WorkerResult
        """
        raise NotImplementedError
