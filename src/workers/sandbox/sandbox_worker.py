"""沙箱 Worker 编排

完整的沙箱任务执行流程：
创建沙箱 → 注入上下文 → 签发临时 Token → 启动 Pi Agent → 轮询状态 → 回收结果 → 销毁沙箱
"""

# 标准库
from typing import Any, Dict, List, Optional

# 本地模块
from src.config.settings import get_settings
from src.core.exceptions import SandboxError, SandboxExecutionError
from src.core.logging import get_logger
from src.llm.token_manager import issue_sandbox_token
from src.monitoring.pipeline_events import pipeline_step
from src.monitoring.trace_context import get_trace_id
from src.schemas.agent import WorkerResult
from src.schemas.sandbox import SandboxResult, SandboxStatus, SandboxTask
from src.workers.sandbox.ipc import extract_final_answer, get_new_messages, ipc_to_a2ui_events, parse_jsonl
from src.workers.sandbox.pi_agent_config import (
    PI_STATE_FILE,
    build_env_vars,
    build_startup_command,
)
from src.workers.sandbox.sandbox_manager import SandboxManager

logger = get_logger(__name__)


class SandboxWorker:
    """沙箱 Worker

    在 E2B 隔离环境中启动 Pi Agent 自主执行高危任务。
    实现完整的 Micro-ReAct 闭环：Thought → Code → Bash → Reflexion。

    Args:
        sandbox_manager: 沙箱管理器实例
        on_a2ui_event: A2UI 事件回调（可选，用于实时推送前端）
    """

    def __init__(
        self,
        sandbox_manager: Optional[SandboxManager] = None,
        on_a2ui_event: Optional[Any] = None,
    ) -> None:
        self._name = "sandbox_worker"
        self._manager = sandbox_manager or SandboxManager()
        self._on_a2ui_event = on_a2ui_event

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, task: SandboxTask) -> SandboxResult:
        """执行沙箱任务

        Args:
            task: 沙箱任务描述

        Returns:
            SandboxResult: 沙箱执行结果
        """
        trace_id = get_trace_id()
        settings = get_settings()
        sandbox_id = ""

        logger.info(
            f"[SandboxWorker] 开始沙箱任务 | "
            f"task_id={task.task_id} instruction_len={len(task.instruction)}"
        )

        try:
            # 1. 确定 LLM Token（本地模式直接用真实 key，E2B 模式签发临时 token）
            if self._manager.is_local:
                temp_token = settings.llm.openai_api_key
            else:
                temp_token = issue_sandbox_token(
                    sandbox_id="pending",
                    task_id=task.task_id,
                )

            # 2. 注入环境变量
            env_vars = build_env_vars(
                llm_token=temp_token,
                llm_base_url=settings.llm.openai_api_base,
                extra_env=task.env_vars,
            )
            task_with_env = SandboxTask(
                task_id=task.task_id,
                instruction=task.instruction,
                context_files=task.context_files,
                env_vars=env_vars,
                timeout=task.timeout,
            )

            # 3. 创建沙箱
            async with pipeline_step("worker.sandbox.create", metadata={
                "task_id": task.task_id,
            }) as ev:
                sandbox_id = await self._manager.create_sandbox(task_with_env)
                ev.add_metadata(sandbox_id=sandbox_id)

            # 获取实际工作目录（本地模式为临时目录，E2B 模式为配置路径）
            work_dir = self._manager.get_work_dir(sandbox_id)

            # 4. 构建并写入启动脚本
            startup_cmd = build_startup_command(
                work_dir=work_dir,
                instruction=task.instruction,
                llm_token=temp_token,
                llm_base_url=settings.llm.openai_api_base,
            )
            await self._manager.write_file(sandbox_id, "start_agent.sh", startup_cmd)

            # 5. 执行 pi --print（同步等待完成，输出写入 state file）
            async with pipeline_step("worker.sandbox.execute", metadata={
                "task_id": task.task_id, "sandbox_id": sandbox_id,
            }) as ev:
                exec_result = await self._manager.execute_command(
                    sandbox_id,
                    f"bash {work_dir}/start_agent.sh",
                    timeout=task.timeout,
                )
                ev.add_metadata(exit_code=exec_result.get("exit_code"))

            logger.info(
                f"[SandboxWorker] pi 执行完成 | "
                f"task_id={task.task_id} exit_code={exec_result.get('exit_code')}"
            )

            # 6. 读取并解析输出
            raw_output = await self._manager.read_state_file(sandbox_id)

            # 优先从 JSONL 提取 final_answer
            final_answer = extract_final_answer(raw_output) if raw_output else ""

            # fallback：直接用 stdout
            if not final_answer and exec_result.get("stdout"):
                final_answer = extract_final_answer(exec_result["stdout"])

            # 7. 解析 IPC 消息（用于 A2UI 事件推送）
            ipc_messages = parse_jsonl(raw_output) if raw_output else []

            # 推送 A2UI 事件
            if self._on_a2ui_event:
                events = ipc_to_a2ui_events(ipc_messages, trace_id)
                for event in events:
                    await self._on_a2ui_event(event)

            # 8. 回收产物
            artifacts = await self._manager.collect_artifacts(
                sandbox_id,
                artifact_paths=self._detect_artifacts(ipc_messages),
            )

            success = bool(final_answer) or exec_result.get("exit_code") == 0

            result = SandboxResult(
                task_id=task.task_id,
                sandbox_id=sandbox_id,
                success=success,
                final_answer=final_answer,
                artifacts=artifacts,
                iterations_used=len([m for m in ipc_messages if m.phase.value == "action"]),
                ipc_log=ipc_messages,
            )

            logger.info(
                f"[SandboxWorker] 沙箱任务完成 | "
                f"task_id={task.task_id} sandbox_id={sandbox_id} "
                f"success={success} answer_len={len(final_answer)}"
            )
            return result

        except SandboxError:
            raise
        except Exception as e:
            logger.error(
                f"[SandboxWorker] 沙箱任务失败 | "
                f"task_id={task.task_id} error={e}",
                exc_info=True,
            )
            return SandboxResult(
                task_id=task.task_id,
                sandbox_id=sandbox_id,
                success=False,
                error=str(e),
            )
        finally:
            # 9. 销毁沙箱
            if sandbox_id:
                async with pipeline_step("worker.sandbox.destroy", metadata={
                    "sandbox_id": sandbox_id,
                }):
                    await self._manager.destroy_sandbox(sandbox_id)

    def _detect_artifacts(self, messages: list) -> list[str]:
        """从 IPC 消息中检测产物文件路径"""
        artifact_paths = []
        for msg in messages:
            if msg.tool_name == "Write" and msg.tool_input:
                path = msg.tool_input.get("path", "")
                if path and not path.startswith("."):
                    artifact_paths.append(path)
        return artifact_paths
