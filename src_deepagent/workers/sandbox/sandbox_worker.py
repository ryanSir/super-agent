"""SandboxWorker — E2B 沙箱编排

编排沙箱生命周期：创建 → 注入文件 → 写入启动脚本 → 执行 Pi Agent → 解析输出 → 销毁。
"""

from __future__ import annotations

import uuid
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.llm.token_manager import issue_sandbox_token
from src_deepagent.schemas.agent import TaskNode, TaskType, WorkerResult
from src_deepagent.schemas.sandbox import Artifact, SandboxResult, SandboxTask
from src_deepagent.workers.base import BaseWorker
from src_deepagent.workers.sandbox.ipc import (
    extract_artifacts,
    extract_final_answer,
    parse_jsonl_output,
)
from src_deepagent.workers.sandbox.pi_agent_config import (
    PI_STATE_FILE,
    build_startup_command,
)
from src_deepagent.workers.sandbox.sandbox_manager import SandboxManager

logger = get_logger(__name__)


class SandboxWorker(BaseWorker):
    """沙箱 Worker — 编排 Pi Agent 在隔离环境中执行"""

    def __init__(self) -> None:
        self._manager = SandboxManager()

    @property
    def name(self) -> str:
        return "sandbox_worker"

    async def _do_execute(self, task: TaskNode) -> WorkerResult:
        """编排沙箱执行流程"""
        settings = get_settings()
        instruction = task.input_data.get("instruction", "")
        context_files = task.input_data.get("context_files", {})
        timeout = task.input_data.get("timeout", 120)

        sandbox_id = f"sb-{uuid.uuid4().hex[:8]}"
        sandbox = await self._manager.create(sandbox_id)
        work_dir = sandbox.get("work_dir", "/tmp")

        try:
            # 1. 确定 LLM Token（本地模式用真实 key，E2B 模式签发临时 token）
            if self._manager._is_local:
                llm_token = settings.llm.api_key
                logger.info(f"使用真实 API Key（本地模式）| sandbox_id={sandbox_id}")
            else:
                llm_token = issue_sandbox_token(sandbox_id, task_id=task.task_id)
                logger.info(f"签发临时 Token（E2B 模式）| sandbox_id={sandbox_id}")

            llm_base_url = settings.llm.base_url

            # 2. 注入上下文文件
            for path, content in context_files.items():
                await self._manager.write_file(sandbox, path, content)
                logger.info(f"注入文件 | sandbox_id={sandbox_id} path={path} size={len(content)}")

            # 3. 构建启动脚本
            startup_script = build_startup_command(
                work_dir=work_dir,
                instruction=instruction,
                llm_token=llm_token,
                llm_base_url=llm_base_url,
            )
            await self._manager.write_file(sandbox, "start_agent.sh", startup_script)
            logger.info(
                f"启动脚本写入 | sandbox_id={sandbox_id} "
                f"instruction_len={len(instruction)} timeout={timeout}s"
            )

            # 4. 执行启动脚本
            command = f"bash {work_dir}/start_agent.sh"
            logger.info(f"开始执行 Pi Agent | sandbox_id={sandbox_id} command={command[:200]}")
            exec_result = await self._manager.execute(
                sandbox,
                command,
                timeout=timeout,
            )

            logger.info(
                f"Pi Agent 执行完成 | task_id={task.task_id} sandbox_id={sandbox_id} "
                f"exit_code={exec_result.get('exit_code')} "
                f"stdout_len={len(exec_result.get('stdout', ''))} "
                f"stderr_len={len(exec_result.get('stderr', ''))}"
            )
            if exec_result.get('stderr'):
                logger.warning(
                    f"Pi Agent stderr | sandbox_id={sandbox_id} "
                    f"stderr={exec_result['stderr'][:500]}"
                )

            # 5. 读取状态文件（Pi Agent 输出写入 state file）
            state_file_path = f"{work_dir}/{PI_STATE_FILE}"
            raw_output = ""
            try:
                raw_output = await self._manager.read_file(sandbox, PI_STATE_FILE)
            except Exception:
                # fallback: 用 stdout
                raw_output = exec_result.get("stdout", "")

            # 6. 解析 JSONL 输出
            events = parse_jsonl_output(raw_output)
            answer = extract_final_answer(events)
            artifacts_data = extract_artifacts(events)

            # fallback: 如果 JSONL 没有 answer，用 stdout
            if not answer and exec_result.get("stdout"):
                fallback_events = parse_jsonl_output(exec_result["stdout"])
                answer = extract_final_answer(fallback_events)

            success = exec_result.get("exit_code", 1) == 0

            return WorkerResult(
                task_id=task.task_id,
                success=success,
                data={
                    "answer": answer,
                    "stdout": exec_result.get("stdout", "")[:5000],
                    "stderr": exec_result.get("stderr", "")[:2000],
                    "exit_code": exec_result.get("exit_code", 1),
                    "artifacts": artifacts_data,
                    "event_count": len(events),
                },
                error="" if success else exec_result.get("stderr", "")[:500],
                metadata={"sandbox_id": sandbox_id},
            )
        finally:
            await self._manager.destroy(sandbox)

    async def execute_sandbox_task(self, task: SandboxTask) -> SandboxResult:
        """直接执行 SandboxTask（桥接工具使用）"""
        node = TaskNode(
            task_id=task.task_id,
            task_type=TaskType.SANDBOX_CODING,
            description=task.instruction,
            input_data={
                "instruction": task.instruction,
                "context_files": task.context_files,
                "timeout": task.timeout,
            },
        )
        result = await self.execute(node)
        return SandboxResult(
            task_id=task.task_id,
            success=result.success,
            stdout=result.data.get("stdout", "") if result.data else "",
            stderr=result.data.get("stderr", "") if result.data else "",
            exit_code=result.data.get("exit_code", 1) if result.data else 1,
            artifacts=[
                Artifact(name=a.get("name", ""), path=a.get("path", ""))
                for a in (result.data.get("artifacts", []) if result.data else [])
            ],
            error=result.error,
        )
