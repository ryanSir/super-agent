"""Claude Agent SDK 实现 — 对标 pi-mono 的自主执行能力

用 Anthropic Messages API + tool_use 实现 agentic loop，
提供与 pi-mono 相同的 4 个原子工具：read / bash / edit / write。
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import anthropic

# ── 工具定义（对标 pi-mono 的 ATOMIC_TOOLS） ──────────────────

TOOLS = [
    {
        "name": "bash",
        "description": "Execute a bash command and return stdout/stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit",
        "description": "Replace a specific string in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_string": {"type": "string", "description": "Text to find"},
                "new_string": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
]


# ── 工具执行器 ────────────────────────────────────────────────

def execute_tool(name: str, input_data: dict[str, Any], work_dir: str) -> str:
    """执行单个工具调用，返回结果文本"""

    if name == "bash":
        return _exec_bash(input_data["command"], input_data.get("timeout", 60), work_dir)
    elif name == "read":
        return _exec_read(input_data["path"], work_dir)
    elif name == "write":
        return _exec_write(input_data["path"], input_data["content"], work_dir)
    elif name == "edit":
        return _exec_edit(input_data["path"], input_data["old_string"], input_data["new_string"], work_dir)
    else:
        return f"Unknown tool: {name}"


def _resolve_path(path: str, work_dir: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(work_dir, path)


def _exec_bash(command: str, timeout: int, work_dir: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=work_dir,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        output += f"\n[exit_code: {result.returncode}]"
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"[error] Command timed out after {timeout}s"
    except Exception as e:
        return f"[error] {e}"


def _exec_read(path: str, work_dir: str) -> str:
    try:
        full_path = _resolve_path(path, work_dir)
        return Path(full_path).read_text(encoding="utf-8")
    except Exception as e:
        return f"[error] {e}"


def _exec_write(path: str, content: str, work_dir: str) -> str:
    try:
        full_path = _resolve_path(path, work_dir)
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        Path(full_path).write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"[error] {e}"


def _exec_edit(path: str, old_string: str, new_string: str, work_dir: str) -> str:
    try:
        full_path = _resolve_path(path, work_dir)
        text = Path(full_path).read_text(encoding="utf-8")
        if old_string not in text:
            return f"[error] old_string not found in {path}"
        new_text = text.replace(old_string, new_string, 1)
        Path(full_path).write_text(new_text, encoding="utf-8")
        return f"Edited {path}: replaced 1 occurrence"
    except Exception as e:
        return f"[error] {e}"


# ── Claude Agent 核心 ─────────────────────────────────────────

class ClaudeAgent:
    """基于 Anthropic Messages API 的 Agentic Loop 实现

    对标 pi-mono：接收自然语言指令 → 自主调用工具完成任务 → 返回结果。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "claude-4.6-opus",
        max_turns: int = 20,
        work_dir: str | None = None,
    ):
        base = base_url or os.getenv("OPENAI_API_BASE", "")
        if base.endswith("/v1"):
            base = base[:-3]

        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base or anthropic.NOT_GIVEN,
            default_headers={
                "Authorization": f"Bearer {api_key or os.getenv('OPENAI_API_KEY', '')}",
            },
        )
        self.model = model
        self.max_turns = max_turns
        self.work_dir = work_dir or os.getcwd()

    def run(self, instruction: str, system_prompt: str | None = None) -> AgentResult:
        """同步执行 agentic loop"""

        system = system_prompt or (
            "You are a coding agent. Use the provided tools to complete the task. "
            "Be concise and efficient. When done, provide a final summary."
        )

        messages: list[dict] = [{"role": "user", "content": instruction}]
        all_events: list[dict] = []
        turn = 0

        print(f"\n{'='*60}")
        print(f"[ClaudeAgent] instruction: {instruction[:100]}...")
        print(f"[ClaudeAgent] model={self.model} work_dir={self.work_dir}")
        print(f"{'='*60}\n")

        while turn < self.max_turns:
            turn += 1
            t0 = time.time()

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": system}],
                tools=TOOLS,
                messages=messages,
            )

            elapsed = time.time() - t0
            all_events.append({
                "turn": turn,
                "stop_reason": response.stop_reason,
                "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens},
                "elapsed": round(elapsed, 2),
            })

            print(f"[Turn {turn}] stop_reason={response.stop_reason} "
                  f"tokens=({response.usage.input_tokens}in/{response.usage.output_tokens}out) "
                  f"elapsed={elapsed:.1f}s")

            # 提取文本和工具调用
            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                    print(f"  [text] {block.text[:200]}")
                elif block.type == "tool_use":
                    tool_calls.append(block)
                    print(f"  [tool] {block.name}({json.dumps(block.input, ensure_ascii=False)[:150]})")

            # 如果没有工具调用，任务完成
            if response.stop_reason == "end_turn" or not tool_calls:
                return AgentResult(
                    success=True,
                    answer="\n".join(text_parts),
                    turns=turn,
                    events=all_events,
                )

            # 执行工具调用，构建 tool_result
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tc in tool_calls:
                result_text = execute_tool(tc.name, tc.input, self.work_dir)
                print(f"  [result] {tc.name} → {result_text[:150]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_text,
                })
                all_events.append({
                    "turn": turn,
                    "tool": tc.name,
                    "input": tc.input,
                    "result": result_text[:500],
                })

            messages.append({"role": "user", "content": tool_results})

        return AgentResult(
            success=False,
            answer="Max turns reached",
            turns=turn,
            events=all_events,
        )


class AgentResult:
    """执行结果，对标 pi-mono 的 WorkerResult"""

    def __init__(self, success: bool, answer: str, turns: int, events: list[dict]):
        self.success = success
        self.answer = answer
        self.turns = turns
        self.events = events

    def __repr__(self) -> str:
        return f"AgentResult(success={self.success}, turns={self.turns}, answer={self.answer[:100]}...)"

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "answer": self.answer,
            "turns": self.turns,
            "events": self.events,
        }


# ── 测试入口 ──────────────────────────────────────────────────

def test_basic():
    """基础测试：让 agent 创建一个文件并验证"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="claude-agent-test-")
    print(f"\n[test] work_dir={work_dir}")

    agent = ClaudeAgent(work_dir=work_dir)

    result = agent.run(
        "Create a Python file called hello.py that prints 'Hello from Claude Agent'. "
        "Then run it and confirm the output."
    )

    print(f"\n{'='*60}")
    print(f"[Result] success={result.success} turns={result.turns}")
    print(f"[Answer] {result.answer}")
    print(f"{'='*60}")

    # 验证文件是否创建
    hello_path = os.path.join(work_dir, "hello.py")
    assert os.path.exists(hello_path), f"hello.py not created at {hello_path}"
    print(f"[Verify] hello.py exists ✓")

    return result


def test_edit():
    """编辑测试：创建文件 → 编辑 → 验证"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="claude-agent-test-")
    agent = ClaudeAgent(work_dir=work_dir)

    result = agent.run(
        "1. Create a file called app.py with a function greet(name) that returns 'Hello, {name}'\n"
        "2. Edit it to also return the greeting in uppercase\n"
        "3. Read the file to confirm the changes\n"
        "4. Run the file with a test call"
    )

    print(f"\n[Result] success={result.success} turns={result.turns}")
    print(f"[Answer] {result.answer}")
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    test_name = sys.argv[1] if len(sys.argv) > 1 else "basic"

    if test_name == "basic":
        test_basic()
    elif test_name == "edit":
        test_edit()
    elif test_name == "all":
        test_basic()
        test_edit()
    else:
        # 自定义指令模式
        agent = ClaudeAgent()
        result = agent.run(test_name)
        print(result)