"""Skill 执行器

对齐 OpenClaw / Claude 官方标准：
- 不预设执行模式
- 构建 SKILL.md + references + scripts 完整上下文
- 交给 Agent 自主决策如何执行（直接回答 / 调用脚本 / 沙箱编码）
"""

# 标准库
import asyncio
import json
import os
from pathlib import Path
from typing import Optional

# 本地模块
from src.core.logging import get_logger
from src.skills.registry import skill_registry
from src.skills.schema import SkillExecuteRequest, SkillExecuteResult, SkillInfo

logger = get_logger(__name__)


async def execute_skill(request: SkillExecuteRequest) -> SkillExecuteResult:
    """执行 skill

    构建完整 skill 上下文，交给 Agent 自主决策执行方式。

    Args:
        request: 执行请求

    Returns:
        SkillExecuteResult
    """
    skill_info = skill_registry.get(request.skill_name)
    if not skill_info:
        return SkillExecuteResult(
            skill_name=request.skill_name,
            script_name="",
            success=False,
            stderr=f"Skill '{request.skill_name}' 未注册",
            exit_code=-1,
        )

    logger.info(
        f"[SkillExecutor] 执行 skill | "
        f"name={request.skill_name} scripts={skill_info.scripts} args={request.args}"
    )

    # 构建完整 skill 上下文
    context = build_skill_context(skill_info)
    user_args = " ".join(request.args) if request.args else ""

    # 交给 Agent 自主决策执行
    return await _agent_execute(request, skill_info, context, user_args)


async def _agent_execute(
    request: SkillExecuteRequest,
    skill_info: SkillInfo,
    context: str,
    user_args: str,
) -> SkillExecuteResult:
    """Agent 自主决策执行

    Agent 读取 skill 完整上下文后，自主判断：
    - 有 scripts/ 且任务匹配 → 调用脚本
    - 需要编码 → 自主生成代码
    - 纯指令型 → 直接按文档流程输出
    """
    from pydantic_ai import Agent
    from src.llm.config import get_model

    # 构建 Agent 指令
    scripts_info = ""
    if skill_info.scripts:
        scripts_dir = Path(skill_info.metadata.path) / "scripts"
        scripts_info = "\n\n## 可用脚本\n"
        for script_name in skill_info.scripts:
            script_path = scripts_dir / script_name
            if script_path.exists():
                try:
                    code = script_path.read_text(encoding="utf-8")
                    scripts_info += f"\n### {script_name}\n```python\n{code}\n```\n"
                except Exception:
                    scripts_info += f"\n### {script_name} (无法读取)\n"

    system_prompt = f"""你是一个 Skill 执行器。根据提供的 Skill 文档，自主决定最佳执行方式并完成任务。

## Skill 文档
{context}
{scripts_info}

## 执行原则
1. 如果 Skill 包含可直接使用的脚本，说明脚本的调用方式和预期结果
2. 如果需要编写代码，直接生成可执行的代码
3. 如果是纯指令型 Skill，按照文档流程逐步执行并输出结果
4. 始终输出结构化的、有价值的结果"""

    user_prompt = user_args if user_args else "按照 Skill 文档的默认流程执行"

    try:
        model = get_model("execution")
        agent = Agent(model=model, instructions=system_prompt)
        result = await agent.run(user_prompt)
        output_text = result.output if hasattr(result, "output") else str(result)

        logger.info(
            f"[SkillExecutor] Agent 执行完成 | "
            f"name={request.skill_name} output_len={len(output_text)}"
        )

        return SkillExecuteResult(
            skill_name=request.skill_name,
            script_name="",
            success=True,
            stdout=output_text,
            exit_code=0,
        )

    except Exception as e:
        logger.error(
            f"[SkillExecutor] Agent 执行失败 | name={request.skill_name} error={e}",
            exc_info=True,
        )
        return SkillExecuteResult(
            skill_name=request.skill_name,
            script_name="",
            success=False,
            stderr=str(e),
            exit_code=-1,
        )


# ============================================================
# 直接脚本执行（供 Agent 或外部调用）
# ============================================================

async def run_script(
    skill_name: str,
    script_name: str,
    args: list[str] = None,
    env: dict[str, str] = None,
    timeout: int = 60,
) -> SkillExecuteResult:
    """直接执行 skill 脚本（不经过 Agent 决策）

    供 Agent 在自主决策后显式调用，或外部 API 直接调用。
    """
    skill_info = skill_registry.get(skill_name)
    if not skill_info:
        return SkillExecuteResult(
            skill_name=skill_name, script_name=script_name,
            success=False, stderr=f"Skill '{skill_name}' 未注册", exit_code=-1,
        )

    script_path = Path(skill_info.metadata.path) / "scripts" / script_name
    if not script_path.exists():
        return SkillExecuteResult(
            skill_name=skill_name, script_name=script_name,
            success=False, stderr=f"脚本不存在: {script_path}", exit_code=-1,
        )

    cmd = _build_command(script_path, args or [])
    run_env = _build_env(skill_info, env)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=run_env,
            cwd=skill_info.metadata.path,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()
        exit_code = proc.returncode or 0

        output_data = None
        if stdout_str:
            try:
                output_data = json.loads(stdout_str)
            except json.JSONDecodeError:
                pass

        return SkillExecuteResult(
            skill_name=skill_name, script_name=script_name,
            success=exit_code == 0, stdout=stdout_str, stderr=stderr_str,
            exit_code=exit_code, output_data=output_data,
        )

    except asyncio.TimeoutError:
        return SkillExecuteResult(
            skill_name=skill_name, script_name=script_name,
            success=False, stderr=f"执行超时 ({timeout}s)", exit_code=-1,
        )
    except Exception as e:
        return SkillExecuteResult(
            skill_name=skill_name, script_name=script_name,
            success=False, stderr=str(e), exit_code=-1,
        )


# ============================================================
# 工具函数
# ============================================================

def build_skill_context(skill_info: SkillInfo) -> str:
    """构建 skill 完整上下文（SKILL.md + references）"""
    parts = []

    if skill_info.doc_content:
        parts.append(skill_info.doc_content)

    refs_dir = Path(skill_info.metadata.path) / "references"
    if refs_dir.exists():
        for ref_file in sorted(refs_dir.iterdir()):
            if ref_file.is_file() and ref_file.suffix in (".md", ".txt", ".json", ".yaml", ".yml"):
                try:
                    content = ref_file.read_text(encoding="utf-8")
                    parts.append(f"\n---\n## Reference: {ref_file.name}\n{content}")
                except Exception:
                    pass

    return "\n\n".join(parts)


def collect_skill_files(skill_info: SkillInfo) -> dict:
    """收集 skill 目录下所有文件（用于沙箱注入）"""
    skill_dir = Path(skill_info.metadata.path)
    context_files = {}

    for file_path in skill_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.stat().st_size > 1024 * 1024:
            continue

        relative = str(file_path.relative_to(skill_dir))
        try:
            context_files[relative] = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, Exception):
            pass

    return context_files


def _build_env(skill_info, extra_env: dict = None) -> dict:
    """构建脚本执行环境变量

    继承当前进程环境，注入 CLAUDE_SKILL_DIR 和调用方传入的额外变量。
    """
    import os
    env = os.environ.copy()
    env["CLAUDE_SKILL_DIR"] = str(skill_info.metadata.path)
    if extra_env:
        env.update(extra_env)
    return env


def _build_command(script_path: Path, args: list) -> list:
    """构建本地执行命令"""
    suffix = script_path.suffix.lower()
    if suffix == ".py":
        return ["python", str(script_path)] + args
    elif suffix == ".sh":
        return ["bash", str(script_path)] + args
    elif suffix in (".js", ".ts"):
        return ["node", str(script_path)] + args
    else:
        return [str(script_path)] + args
