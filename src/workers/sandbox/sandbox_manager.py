"""E2B 沙箱生命周期管理

负责沙箱的创建、文件注入、命令执行、状态监听、产物回收和销毁。
支持三种 Provider：
  - tencent / e2b：远程 E2B 沙箱（生产）
  - local：本地临时目录 + subprocess（开发/测试降级）
"""

# 标准库
import asyncio
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

# 本地模块
from src.config.settings import get_settings
from src.core.exceptions import (
    SandboxCreationError,
    SandboxExecutionError,
    SandboxTimeoutError,
)
from src.core.logging import get_logger
from src.schemas.sandbox import Artifact, SandboxResult, SandboxStatus, SandboxTask

logger = get_logger(__name__)


class SandboxManager:
    """沙箱生命周期管理器

    根据 SANDBOX_PROVIDER 自动选择执行后端：
    - tencent / e2b：远程 E2B 沙箱
    - local：本地临时目录（开发降级，无隔离）
    """

    def __init__(self) -> None:
        self._settings = get_settings().e2b
        self._active_sandboxes: Dict[str, Any] = {}
        # local 模式下存储临时目录路径
        self._local_dirs: Dict[str, str] = {}

    @property
    def is_local(self) -> bool:
        return self._settings.sandbox_provider == "local"

    def get_work_dir(self, sandbox_id: str) -> str:
        """获取沙箱实际工作目录（本地模式返回临时目录，E2B 模式返回配置路径）"""
        if self.is_local:
            return self._local_dirs.get(sandbox_id, self._settings.e2b_work_dir)
        return self._settings.e2b_work_dir

    # ============================================================
    # 公共接口
    # ============================================================

    async def create_sandbox(self, task: SandboxTask) -> str:
        if self.is_local:
            return await self._local_create(task)
        return await self._e2b_create(task)

    async def execute_command(
        self,
        sandbox_id: str,
        command: str,
        timeout: int = 120,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.is_local:
            return await self._local_exec(sandbox_id, command, timeout, cwd)
        return await self._e2b_exec(sandbox_id, command, timeout, cwd)

    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        if self.is_local:
            work_dir = self._local_dirs.get(sandbox_id, "")
            full_path = Path(work_dir) / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return

        sandbox = self._active_sandboxes.get(sandbox_id)
        if not sandbox:
            raise SandboxExecutionError(f"沙箱不存在: {sandbox_id}")
        full_path = f"{self._settings.e2b_work_dir}/{path}"
        await sandbox.files.write(full_path, content)

    async def read_file(self, sandbox_id: str, path: str) -> str:
        if self.is_local:
            work_dir = self._local_dirs.get(sandbox_id, "")
            full_path = Path(work_dir) / path
            if not full_path.exists():
                raise FileNotFoundError(f"文件不存在: {full_path}")
            return full_path.read_text(encoding="utf-8")

        sandbox = self._active_sandboxes.get(sandbox_id)
        if not sandbox:
            raise SandboxExecutionError(f"沙箱不存在: {sandbox_id}")
        full_path = f"{self._settings.e2b_work_dir}/{path}"
        content = await sandbox.files.read(full_path)
        return content

    async def read_state_file(self, sandbox_id: str, state_file: str = ".pi_state.jsonl") -> str:
        """读取 Pi Agent 状态文件"""
        try:
            return await self.read_file(sandbox_id, state_file)
        except Exception:
            return ""

    async def collect_artifacts(
        self,
        sandbox_id: str,
        artifact_paths: List[str],
    ) -> List[Artifact]:
        """回收沙箱产物"""
        artifacts = []
        for path in artifact_paths:
            try:
                content = await self.read_file(sandbox_id, path)
                ext = path.rsplit(".", 1)[-1].lower() if "." in path else "txt"
                content_type_map = {
                    "html": "text/html",
                    "py": "text/python",
                    "js": "text/javascript",
                    "json": "application/json",
                    "csv": "text/csv",
                    "png": "image/png",
                    "svg": "image/svg+xml",
                }
                content_type = content_type_map.get(ext, "text/plain")
                artifacts.append(Artifact(
                    filename=path,
                    content_type=content_type,
                    content=content,
                    size_bytes=len(content.encode("utf-8")) if content else 0,
                ))
            except Exception as e:
                logger.warning(
                    f"[SandboxManager] 产物回收失败 | "
                    f"sandbox_id={sandbox_id} path={path} error={e}"
                )

        logger.info(
            f"[SandboxManager] 产物回收完成 | "
            f"sandbox_id={sandbox_id} collected={len(artifacts)}/{len(artifact_paths)}"
        )
        return artifacts

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        if self.is_local:
            work_dir = self._local_dirs.pop(sandbox_id, None)
            if work_dir and Path(work_dir).exists():
                shutil.rmtree(work_dir, ignore_errors=True)
                logger.info(f"[SandboxManager] 本地沙箱已清理 | sandbox_id={sandbox_id}")
            return

        sandbox = self._active_sandboxes.pop(sandbox_id, None)
        if sandbox:
            try:
                await sandbox.kill()
                logger.info(f"[SandboxManager] 沙箱已销毁 | sandbox_id={sandbox_id}")
            except Exception as e:
                logger.warning(
                    f"[SandboxManager] 沙箱销毁异常 | sandbox_id={sandbox_id} error={e}"
                )

    async def destroy_all(self) -> None:
        """销毁所有活跃沙箱"""
        sandbox_ids = list(self._active_sandboxes.keys()) + list(self._local_dirs.keys())
        for sid in sandbox_ids:
            await self.destroy_sandbox(sid)

    # ============================================================
    # 本地模式实现
    # ============================================================

    async def _local_create(self, task: SandboxTask) -> str:
        """本地模式：创建临时目录作为沙箱"""
        try:
            work_dir = tempfile.mkdtemp(prefix="sandbox-")
            sandbox_id = f"local-{uuid.uuid4().hex[:12]}"
            self._local_dirs[sandbox_id] = work_dir

            # 注入上下文文件
            for filepath, content in task.context_files.items():
                full_path = Path(work_dir) / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

            # 注入环境变量文件
            if task.env_vars:
                env_lines = "\n".join(f'export {k}="{v}"' for k, v in task.env_vars.items())
                (Path(work_dir) / ".env.sh").write_text(env_lines, encoding="utf-8")

            logger.info(
                f"[SandboxManager] 本地沙箱创建成功 | "
                f"sandbox_id={sandbox_id} work_dir={work_dir} task_id={task.task_id}"
            )
            return sandbox_id

        except Exception as e:
            raise SandboxCreationError(
                f"本地沙箱创建失败: {e}",
                context={"task_id": task.task_id, "provider": "local"},
            ) from e

    async def _local_exec(
        self,
        sandbox_id: str,
        command: str,
        timeout: int,
        cwd: Optional[str],
    ) -> Dict[str, Any]:
        """本地模式：在临时目录里执行命令"""
        work_dir = self._local_dirs.get(sandbox_id)
        if not work_dir:
            raise SandboxExecutionError(
                f"本地沙箱不存在: {sandbox_id}",
                context={"sandbox_id": sandbox_id},
            )

        run_dir = cwd or work_dir
        # 确保 nvm 管理的 node 在 PATH 中（PyCharm 等 IDE 启动时不加载 shell profile）
        nvm_dir = os.environ.get("NVM_DIR", os.path.expanduser("~/.nvm"))
        nvm_node_bin = os.path.join(nvm_dir, "versions", "node")
        extra_path = ""
        if os.path.isdir(nvm_node_bin):
            # 取最新版本的 bin 目录
            versions = sorted(os.listdir(nvm_node_bin), reverse=True)
            if versions:
                extra_path = os.path.join(nvm_node_bin, versions[0], "bin")
        current_path = os.environ.get("PATH", "")
        if extra_path and extra_path not in current_path:
            current_path = f"{extra_path}:{current_path}"
        env = {**os.environ, "SANDBOX_WORK_DIR": work_dir, "PATH": current_path}

        import shutil
        logger.info(
            f"[SandboxManager] 本地执行环境 | "
            f"PATH={env.get('PATH', '')[:200]} "
            f"which_node={shutil.which('node', path=env.get('PATH', ''))} "
            f"which_pi={shutil.which('pi', path=env.get('PATH', ''))} "
            f"command={command[:200]}"
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=run_dir,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            logger.info(
                f"[SandboxManager] 本地执行完成 | "
                f"exit_code={proc.returncode} "
                f"stdout_len={len(stdout)} stderr_len={len(stderr)} "
                f"stderr_head={stderr[:500]}"
            )
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError as e:
            raise SandboxTimeoutError(
                f"本地沙箱命令超时: {command[:100]}",
                context={"sandbox_id": sandbox_id, "timeout": timeout},
            ) from e
        except Exception as e:
            raise SandboxExecutionError(
                f"本地沙箱命令执行失败: {e}",
                context={"sandbox_id": sandbox_id, "command": command[:200]},
            ) from e

    # ============================================================
    # E2B 模式实现
    # ============================================================

    async def _e2b_create(self, task: SandboxTask) -> str:
        """E2B 模式：创建远程沙箱"""
        try:
            from e2b import AsyncSandbox

            sandbox = await AsyncSandbox.create(
                template=self._settings.e2b_template,
                timeout=self._settings.e2b_timeout,
                api_key=self._settings.e2b_api_key,
                domain=self._settings.e2b_domain,
            )
            sandbox_id = sandbox.sandbox_id

            for filepath, content in task.context_files.items():
                full_path = f"{self._settings.e2b_work_dir}/{filepath}"
                await sandbox.files.write(full_path, content)

            if task.env_vars:
                env_script = "\n".join(
                    f'export {k}="{v}"' for k, v in task.env_vars.items()
                )
                await sandbox.files.write(
                    f"{self._settings.e2b_work_dir}/.env.sh", env_script
                )

            self._active_sandboxes[sandbox_id] = sandbox

            logger.info(
                f"[SandboxManager] 沙箱创建成功 | "
                f"sandbox_id={sandbox_id} task_id={task.task_id} "
                f"files={len(task.context_files)} timeout={self._settings.e2b_timeout}s"
            )
            return sandbox_id

        except Exception as e:
            raise SandboxCreationError(
                f"沙箱创建失败: {e}",
                context={"task_id": task.task_id, "provider": self._settings.sandbox_provider},
            ) from e

    async def _e2b_exec(
        self,
        sandbox_id: str,
        command: str,
        timeout: int,
        cwd: Optional[str],
    ) -> Dict[str, Any]:
        """E2B 模式：在远程沙箱执行命令"""
        sandbox = self._active_sandboxes.get(sandbox_id)
        if not sandbox:
            raise SandboxExecutionError(
                f"沙箱不存在: {sandbox_id}",
                context={"sandbox_id": sandbox_id},
            )

        work_dir = cwd or self._settings.e2b_work_dir

        try:
            result = await sandbox.commands.run(
                command,
                timeout=timeout,
                cwd=work_dir,
                user="root",
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            }
        except TimeoutError as e:
            raise SandboxTimeoutError(
                f"沙箱命令超时: {command[:100]}",
                context={"sandbox_id": sandbox_id, "timeout": timeout},
            ) from e
        except Exception as e:
            raise SandboxExecutionError(
                f"沙箱命令执行失败: {e}",
                context={"sandbox_id": sandbox_id, "command": command[:200]},
            ) from e
