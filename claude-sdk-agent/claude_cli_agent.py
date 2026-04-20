"""Claude Code CLI Agent 测试 — 通过 `claude -p` 子进程模式执行

对标 pi_agent.py 的 `pi --print --mode json`，用 Claude Code CLI 做同样的事。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class ClaudeCliAgent:
    """Claude Code CLI 封装，通过 `claude -p` 子进程执行"""

    def __init__(
        self,
        model: str | None = None,
        tools: str = "Read,Edit,Bash,Write",
        work_dir: str | None = None,
    ):
        self.model = model
        self.tools = tools
        self.work_dir = work_dir or os.getcwd()

    def run(self, instruction: str, timeout: int = 180) -> AgentResult:
        """执行 claude -p，返回结构化结果"""

        print(f"\n{'='*60}")
        print(f"[ClaudeCliAgent] instruction: {instruction[:100]}...")
        print(f"[ClaudeCliAgent] tools={self.tools} work_dir={self.work_dir}")
        print(f"{'='*60}\n")

        cmd = [
            "claude",
            "-p", instruction,
            "--output-format", "json",
            "--allowedTools", self.tools,
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        t0 = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                env={**os.environ},
            )
            elapsed = time.time() - t0

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            return AgentResult(
                success=False,
                answer=f"Timeout after {timeout}s",
                elapsed=elapsed,
                raw_output="",
                turns=0,
                usage={},
                cost=0,
            )

        # 解析 JSON 输出
        parsed = {}
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            print(f"  [warn] Failed to parse JSON output, raw: {stdout[:300]}")

        answer = parsed.get("result", "")
        num_turns = parsed.get("num_turns", 0)
        duration_ms = parsed.get("duration_ms", 0)
        duration_api_ms = parsed.get("duration_api_ms", 0)
        usage = parsed.get("usage", {})
        model_usage = parsed.get("modelUsage", {})
        total_cost = parsed.get("total_cost_usd", 0)
        session_id = parsed.get("session_id", "")
        stop_reason = parsed.get("stop_reason", "")
        is_error = parsed.get("is_error", False)

        # 提取 token 统计
        total_input = usage.get("input_tokens", 0)
        total_output = usage.get("output_tokens", 0)

        print(f"  [result] stop_reason={stop_reason} turns={num_turns} "
              f"tokens=({total_input}in/{total_output}out) "
              f"elapsed={elapsed:.1f}s api_ms={duration_api_ms}ms "
              f"cost=${total_cost:.4f}")
        if answer:
            print(f"  [answer] {answer[:200]}")
        if stderr:
            print(f"  [stderr] {stderr[:200]}")

        return AgentResult(
            success=(exit_code == 0 and not is_error),
            answer=answer,
            elapsed=elapsed,
            raw_output=stdout[:5000],
            turns=num_turns,
            usage={
                "input_tokens": total_input,
                "output_tokens": total_output,
                "model_usage": model_usage,
            },
            cost=total_cost,
            session_id=session_id,
            duration_api_ms=duration_api_ms,
        )


class AgentResult:
    """执行结果"""

    def __init__(
        self,
        success: bool,
        answer: str,
        elapsed: float,
        raw_output: str = "",
        turns: int = 0,
        usage: dict | None = None,
        cost: float = 0,
        session_id: str = "",
        duration_api_ms: int = 0,
    ):
        self.success = success
        self.answer = answer
        self.elapsed = elapsed
        self.raw_output = raw_output
        self.turns = turns
        self.usage = usage or {}
        self.cost = cost
        self.session_id = session_id
        self.duration_api_ms = duration_api_ms

    def __repr__(self) -> str:
        return (f"AgentResult(success={self.success}, elapsed={self.elapsed:.1f}s, "
                f"turns={self.turns}, cost=${self.cost:.4f}, answer={self.answer[:80]}...)")


# ── 测试用例 ──────────────────────────────────────────────────

def test_basic():
    """基础测试：创建文件 + 执行"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="claude-cli-test-")
    print(f"\n[test] work_dir={work_dir}")

    agent = ClaudeCliAgent(work_dir=work_dir)
    result = agent.run(
        "Create a Python file called hello.py that prints 'Hello from Claude Agent'. "
        "Then run it and confirm the output."
    )

    print(f"\n{'='*60}")
    print(f"[Result] success={result.success} elapsed={result.elapsed:.1f}s turns={result.turns}")
    print(f"[Answer] {result.answer}")
    print(f"{'='*60}")

    hello_path = os.path.join(work_dir, "hello.py")
    assert os.path.exists(hello_path), f"hello.py not created at {hello_path}"
    print(f"[Verify] hello.py exists ✓")

    return result


def test_edit():
    """编辑测试"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="claude-cli-test-")
    agent = ClaudeCliAgent(work_dir=work_dir)

    result = agent.run(
        "1. Create a file called app.py with a function greet(name) that returns 'Hello, {name}'\n"
        "2. Edit it to also return the greeting in uppercase\n"
        "3. Read the file to confirm the changes\n"
        "4. Run the file with a test call"
    )

    print(f"\n[Result] success={result.success} elapsed={result.elapsed:.1f}s")
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
        agent = ClaudeCliAgent()
        result = agent.run(test_name)
        print(result)