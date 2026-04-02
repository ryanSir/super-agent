"""Pi Agent 启动配置

定义 E2B 沙箱内 Pi Agent 的启动参数和 JSONL 输出配置。
适配 pi v0.62+ 的参数格式（--print --mode json）。
"""

# 标准库
from typing import Dict, List

# Pi Agent 原子工具集（沙箱内仅提供最底层能力）
ATOMIC_TOOLS = "read,bash,edit,write"

# Pi Agent 状态文件路径（IPC 通信）
PI_STATE_FILE = ".pi_state.jsonl"

# Pi Agent 启动脚本模板（适配 pi v0.62+）
# 用单引号 heredoc 写入 instruction 文件，避免 shell 转义问题
PI_AGENT_STARTUP_SCRIPT = """#!/bin/bash
# Pi Agent 启动脚本 — 非交互模式，JSONL 结构化输出

# 加载 nvm（本地模式需要，确保使用正确的 Node 版本）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

export OPENAI_API_KEY="{llm_token}"
export OPENAI_BASE_URL="{llm_base_url}"

cd {work_dir}

# 将 instruction 写入临时文件（单引号 heredoc 不做任何 shell 展开）
cat > {work_dir}/.pi_instruction.txt << 'PI_INSTRUCTION_EOF'
{instruction}
PI_INSTRUCTION_EOF

pi --print --mode json \\
    --provider {provider} \\
    --model {model} \\
    --tools {tools} \\
    --no-session \\
    "$(cat {work_dir}/.pi_instruction.txt)" > "{work_dir}/{state_file}" 2>&1
"""


def build_startup_command(
    work_dir: str,
    instruction: str,
    llm_token: str,
    llm_base_url: str,
    model: str = None,
    max_iterations: int = 10,
    tools: List[str] = None,
) -> str:
    """构建 Pi Agent 启动命令"""
    from src.config.settings import get_settings
    settings = get_settings().e2b
    pi_provider = settings.sandbox_pi_provider
    pi_model = model or settings.sandbox_pi_model
    tool_list = ",".join(tools) if tools else ATOMIC_TOOLS

    return PI_AGENT_STARTUP_SCRIPT.format(
        work_dir=work_dir,
        state_file=PI_STATE_FILE,
        instruction=instruction,
        llm_token=llm_token,
        llm_base_url=llm_base_url,
        provider=pi_provider,
        model=pi_model,
        tools=tool_list,
    )


def build_env_vars(
    llm_token: str,
    llm_base_url: str,
    model: str = "gpt-4o",
    extra_env: Dict[str, str] = None,
) -> Dict[str, str]:
    """构建沙箱环境变量"""
    env = {
        "OPENAI_API_KEY": llm_token,
        "OPENAI_BASE_URL": llm_base_url,
        "PI_MODEL": model,
    }
    if extra_env:
        env.update(extra_env)
    return env

