"""SandboxManager — 沙箱生命周期管理

支持 Local（开发）和 E2B（生产）双后端，透明切换。
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.exceptions import SandboxError, SandboxTimeoutError
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


class SandboxManager:
    """沙箱生命周期管理器"""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def _is_local(self) -> bool:
        return self._settings.e2b.use_local

    # ── 创建 ──────────────────────────────────────────────

    async def create(self, sandbox_id: str) -> dict[str, Any]:
        """创建沙箱实例"""
        if self._is_local:
            return await self._local_create(sandbox_id)
        return await self._e2b_create(sandbox_id)

    async def _local_create(self, sandbox_id: str) -> dict[str, Any]:
        work_dir = tempfile.mkdtemp(prefix=f"sandbox-{sandbox_id}-")
        logger.info(f"本地沙箱创建 | sandbox_id={sandbox_id} dir={work_dir}")
        return {"sandbox_id": sandbox_id, "work_dir": work_dir, "backend": "local"}

    async def _e2b_create(self, sandbox_id: str) -> dict[str, Any]:
        try:
            from e2b import Sandbox

            sandbox = Sandbox(api_key=self._settings.e2b.api_key)
            logger.info(f"E2B 沙箱创建 | sandbox_id={sandbox_id}")
            return {"sandbox_id": sandbox_id, "instance": sandbox, "backend": "e2b"}
        except Exception as e:
            raise SandboxError(f"E2B 沙箱创建失败: {e}") from e

    # ── 执行 ──────────────────────────────────────────────

    async def execute(
        self,
        sandbox: dict[str, Any],
        command: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """在沙箱中执行命令"""
        timeout = timeout or self._settings.e2b.timeout
        if sandbox.get("backend") == "local":
            return await self._local_execute(sandbox, command, timeout)
        return await self._e2b_execute(sandbox, command, timeout)

    async def _local_execute(
        self, sandbox: dict[str, Any], command: str, timeout: int
    ) -> dict[str, Any]:
        work_dir = sandbox["work_dir"]
        sandbox_id = sandbox.get("sandbox_id", "unknown")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 逐行读取 stdout，实时打印 Pi Agent 动态
            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            async def _read_stdout():
                assert proc.stdout is not None
                async for line in proc.stdout:
                    decoded = line.decode(errors="replace").rstrip()
                    stdout_lines.append(decoded)
                    # 解析 JSONL 事件类型用于日志
                    event_type = ""
                    try:
                        import json
                        obj = json.loads(decoded)
                        event_type = obj.get("type", "")
                    except Exception:
                        pass
                    # if event_type:
                    #     logger.info(f"[Pi Agent] {sandbox_id} | event={event_type}")
                    # elif decoded:
                    #     logger.info(f"[Pi Agent] {sandbox_id} | {decoded[:200]}")

            async def _read_stderr():
                assert proc.stderr is not None
                async for line in proc.stderr:
                    decoded = line.decode(errors="replace").rstrip()
                    stderr_lines.append(decoded)
                    if decoded:
                        logger.warning(f"[Pi Agent stderr] {sandbox_id} | {decoded[:300]}")

            await asyncio.wait_for(
                asyncio.gather(_read_stdout(), _read_stderr(), proc.wait()),
                timeout=timeout,
            )

            return {
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            proc.kill()  # type: ignore[union-attr]
            raise SandboxTimeoutError(
                f"沙箱执行超时 ({timeout}s)",
                detail=f"command={command[:200]}",
            )

    async def _e2b_execute(
        self, sandbox: dict[str, Any], command: str, timeout: int
    ) -> dict[str, Any]:
        try:
            instance = sandbox["instance"]
            result = instance.commands.run(command, timeout=timeout)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            }
        except Exception as e:
            if "timeout" in str(e).lower():
                raise SandboxTimeoutError(f"E2B 执行超时: {e}") from e
            raise SandboxError(f"E2B 执行失败: {e}") from e

    # ── 文件操作 ──────────────────────────────────────────

    async def write_file(
        self, sandbox: dict[str, Any], path: str, content: str
    ) -> None:
        """写入文件到沙箱"""
        if sandbox.get("backend") == "local":
            full_path = os.path.join(sandbox["work_dir"], path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            sandbox["instance"].files.write(path, content)

    async def read_file(self, sandbox: dict[str, Any], path: str) -> str:
        """从沙箱读取文件"""
        if sandbox.get("backend") == "local":
            full_path = os.path.join(sandbox["work_dir"], path)
            with open(full_path, encoding="utf-8") as f:
                return f.read()
        return sandbox["instance"].files.read(path)

    # ── 销毁 ──────────────────────────────────────────────

    async def destroy(self, sandbox: dict[str, Any]) -> None:
        """销毁沙箱实例"""
        sandbox_id = sandbox.get("sandbox_id", "unknown")
        if sandbox.get("backend") == "local":
            import shutil

            work_dir = sandbox.get("work_dir", "")
            if work_dir and os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)
            logger.info(f"本地沙箱销毁 | sandbox_id={sandbox_id}")
        else:
            try:
                sandbox["instance"].kill()
            except Exception as e:
                logger.warning(f"E2B 沙箱销毁失败 | sandbox_id={sandbox_id} error={e}")
            logger.info(f"E2B 沙箱销毁 | sandbox_id={sandbox_id}")
