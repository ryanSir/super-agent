"""Pi Agent (pi-mono) 测试 — 对标 claude_agent.py 做性能对比

用 pi CLI 的 --print --mode json 非交互模式执行相同任务，
解析 JSONL 输出，记录耗时和 token 消耗。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class PiAgent:
    """Pi-mono CLI 封装，对标 ClaudeAgent"""

    def __init__(
        self,
        provider: str = "my-gateway",
        model: str = "claude-4.6-opus",
        tools: str = "read,bash,edit,write",
        work_dir: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.tools = tools
        self.work_dir = work_dir or os.getcwd()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_API_BASE", "")

    def run(self, instruction: str, timeout: int = 120) -> AgentResult:
        """执行 pi agent，返回结构化结果"""

        print(f"\n{'='*60}")
        print(f"[PiAgent] instruction: {instruction[:100]}...")
        print(f"[PiAgent] model={self.model} provider={self.provider} work_dir={self.work_dir}")
        print(f"{'='*60}\n")

        # 将 instruction 写入临时文件，避免 shell 转义问题
        inst_file = os.path.join(self.work_dir, ".pi_instruction.txt")
        Path(inst_file).write_text(instruction, encoding="utf-8")

        env = os.environ.copy()
        env["OPENAI_API_KEY"] = self.api_key
        env["OPENAI_BASE_URL"] = self.base_url

        # 加载 nvm 确保 node 可用
        cmd = (
            f'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"; '
            f'cd {self.work_dir} && '
            f'pi --print --mode json '
            f'--provider {self.provider} '
            f'--model {self.model} '
            f'--tools {self.tools} '
            f'--no-session '
            f'"$(cat {inst_file})" 2>&1'
        )

        t0 = time.time()
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.work_dir, env=env,
                executable="/bin/bash",
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
                events=[],
                raw_output="",
            )

        # 解析 JSONL 输出
        events = parse_jsonl_output(stdout)
        answer = extract_final_answer(events)
        tool_calls = extract_tool_calls(events)

        # 打印执行过程
        for i, tc in enumerate(tool_calls, 1):
            print(f"  [tool {i}] {tc['name']}({json.dumps(tc.get('input', {}), ensure_ascii=False)[:150]})")
            if tc.get("result"):
                print(f"  [result] {str(tc['result'])[:150]}")

        print(f"\n[PiAgent] exit_code={exit_code} elapsed={elapsed:.1f}s events={len(events)}")
        if answer:
            print(f"[Answer] {answer[:300]}")

        # fallback: 如果 JSONL 没解析出 answer，用 stdout 最后几行
        if not answer and stdout:
            lines = [l for l in stdout.strip().splitlines() if l.strip() and not l.startswith("{")]
            if lines:
                answer = "\n".join(lines[-5:])

        return AgentResult(
            success=(exit_code == 0),
            answer=answer,
            elapsed=elapsed,
            events=events,
            raw_output=stdout[:5000],
            tool_calls=tool_calls,
        )


class AgentResult:
    """执行结果"""

    def __init__(
        self,
        success: bool,
        answer: str,
        elapsed: float,
        events: list[dict],
        raw_output: str = "",
        tool_calls: list[dict] | None = None,
    ):
        self.success = success
        self.answer = answer
        self.elapsed = elapsed
        self.events = events
        self.raw_output = raw_output
        self.tool_calls = tool_calls or []

    def __repr__(self) -> str:
        return (f"AgentResult(success={self.success}, elapsed={self.elapsed:.1f}s, "
                f"tools={len(self.tool_calls)}, answer={self.answer[:80]}...)")


# ── JSONL 解析（复用 ipc.py 逻辑） ───────────────────────────

def parse_jsonl_output(raw: str) -> list[dict]:
    events = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def extract_final_answer(events: list[dict]) -> str:
    for event in reversed(events):
        etype = event.get("type", "")
        if etype == "agent_end":
            for msg in reversed(event.get("messages", [])):
                if msg.get("role") == "assistant":
                    texts = [c.get("text", "") for c in msg.get("content", []) if c.get("type") == "text"]
                    if texts:
                        return "\n".join(texts)
        if etype in ("turn_end", "message_end"):
            msg = event.get("message", {})
            if msg.get("role") == "assistant":
                texts = [c.get("text", "") for c in msg.get("content", []) if c.get("type") == "text"]
                if texts:
                    return "\n".join(texts)
        if etype == "message_update":
            ae = event.get("assistantMessageEvent", {})
            if ae.get("type") == "text_end":
                return ae.get("content", "")
    return ""


def extract_tool_calls(events: list[dict]) -> list[dict]:
    calls = []
    for event in events:
        etype = event.get("type", "")
        if etype == "tool_use":
            calls.append({
                "name": event.get("name", ""),
                "input": event.get("input", {}),
            })
        elif etype == "tool_result":
            if calls and not calls[-1].get("result"):
                calls[-1]["result"] = str(event.get("result", ""))[:300]
        # pi v3: assistantMessageEvent 中的 tool_use
        if etype == "message_update":
            ae = event.get("assistantMessageEvent", {})
            if ae.get("type") == "tool_use":
                calls.append({
                    "name": ae.get("name", ""),
                    "input": ae.get("input", {}),
                })
    return calls


# ── 测试用例（与 claude_agent.py 完全相同的任务） ─────────────

def test_basic():
    """基础测试：创建文件 + 执行"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="pi-agent-test-")
    print(f"\n[test] work_dir={work_dir}")

    agent = PiAgent(work_dir=work_dir)
    result = agent.run(
        "Create a Python file called hello.py that prints 'Hello from Claude Agent'. "
        "Then run it and confirm the output."
    )

    print(f"\n{'='*60}")
    print(f"[Result] success={result.success} elapsed={result.elapsed:.1f}s")
    print(f"[Answer] {result.answer}")
    print(f"{'='*60}")

    hello_path = os.path.join(work_dir, "hello.py")
    assert os.path.exists(hello_path), f"hello.py not created at {hello_path}"
    print(f"[Verify] hello.py exists ✓")

    return result


def test_edit():
    """编辑测试：创建 → 编辑 → 验证"""
    import tempfile

    work_dir = tempfile.mkdtemp(prefix="pi-agent-test-")
    agent = PiAgent(work_dir=work_dir)

    result = agent.run(
        "1. Create a file called app.py with a function greet(name) that returns 'Hello, {name}'\n"
        "2. Edit it to also return the greeting in uppercase\n"
        "3. Read the file to confirm the changes\n"
        "4. Run the file with a test call"
    )

    print(f"\n[Result] success={result.success} elapsed={result.elapsed:.1f}s")
    print(f"[Answer] {result.answer}")
    return result


# ── 对比运行器 ────────────────────────────────────────────────

def run_comparison():
    """同时运行两个 agent，对比结果"""
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent))
    from claude_agent import ClaudeAgent, AgentResult as ClaudeResult

    instruction = (
        "Create a Python file called hello.py that prints 'Hello from Claude Agent'. "
        "Then run it and confirm the output."
    )

    # ── Pi Agent ──
    pi_dir = tempfile.mkdtemp(prefix="pi-agent-bench-")
    pi_agent = PiAgent(work_dir=pi_dir)
    t0 = time.time()
    pi_result = pi_agent.run(instruction)
    pi_elapsed = time.time() - t0

    # ── Claude Agent ──
    claude_dir = tempfile.mkdtemp(prefix="claude-agent-bench-")
    claude_agent = ClaudeAgent(work_dir=claude_dir)
    t0 = time.time()
    claude_result = claude_agent.run(instruction)
    claude_elapsed = time.time() - t0

    # ── 对比报告 ──
    print(f"\n{'='*60}")
    print(f"  BENCHMARK COMPARISON")
    print(f"{'='*60}")
    print(f"  Task: basic (create + run hello.py)")
    print(f"{'─'*60}")
    print(f"  {'Metric':<25} {'Pi Agent':<18} {'Claude Agent':<18}")
    print(f"{'─'*60}")
    print(f"  {'Total Time':<25} {pi_elapsed:>6.1f}s{'':<11} {claude_elapsed:>6.1f}s")
    print(f"  {'Success':<25} {str(pi_result.success):<18} {str(claude_result.success):<18}")
    print(f"  {'Tool Calls':<25} {len(pi_result.tool_calls):<18} {claude_result.turns:<18}")
    print(f"  {'Model':<25} {pi_agent.model:<18} {claude_agent.model:<18}")
    print(f"{'─'*60}")
    faster = "Pi Agent" if pi_elapsed < claude_elapsed else "Claude Agent"
    diff = abs(pi_elapsed - claude_elapsed)
    print(f"  Winner: {faster} (faster by {diff:.1f}s)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    test_name = sys.argv[1] if len(sys.argv) > 1 else "basic"

    if test_name == "basic":
        test_basic()
    elif test_name == "edit":
        test_edit()
    elif test_name == "compare":
        run_comparison()
    elif test_name == "all":
        test_basic()
        test_edit()
    else:
        agent = PiAgent()
        result = agent.run(test_name)
        print(result)