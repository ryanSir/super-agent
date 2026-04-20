"""Claude API Agent vs Claude CLI Agent vs Pi Agent 三方对比测试

12 个测试用例，从简单到复杂，包含 Skill 执行。
用法:
    python benchmark.py              # 运行全部测试（三方）
    python benchmark.py --case 1     # 运行单个测试
    python benchmark.py --case 1,5,9 # 运行指定测试
    python benchmark.py --agents pi,claude_api          # 只跑指定 agent
    python benchmark.py --agents pi,claude_api,claude_cli  # 三方（默认）
    python benchmark.py --list       # 列出所有测试
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from claude_agent import ClaudeAgent
from claude_agent import AgentResult as ClaudeResult
from claude_cli_agent import ClaudeCliAgent
from pi_agent import PiAgent
from pi_agent import AgentResult as PiResult

ALL_AGENTS = ["pi", "claude_api", "claude_cli"]

# ── 测试用例定义 ──────────────────────────────────────────────

TEST_CASES: list[dict] = [
    # ── Level 1: 简单（单步操作） ──
    {
        "id": 1,
        "name": "单文件创建",
        "level": "simple",
        "instruction": (
            "Create a Python file called hello.py that prints 'Hello World'. "
            "Then run it to verify."
        ),
        "verify": lambda d: os.path.exists(os.path.join(d, "hello.py")),
    },
    {
        "id": 2,
        "name": "Bash 命令执行",
        "level": "simple",
        "instruction": (
            "Run the following commands and report the results:\n"
            "1. echo 'test123' > output.txt\n"
            "2. cat output.txt\n"
            "3. wc -c output.txt"
        ),
        "verify": lambda d: os.path.exists(os.path.join(d, "output.txt")),
    },
    {
        "id": 3,
        "name": "文件读取分析",
        "level": "simple",
        "instruction": (
            "Read the file data.json, count how many items are in the 'users' array, "
            "and report each user's name."
        ),
        "setup": lambda d: Path(os.path.join(d, "data.json")).write_text(json.dumps({
            "users": [
                {"name": "Alice", "age": 30, "role": "engineer"},
                {"name": "Bob", "age": 25, "role": "designer"},
                {"name": "Charlie", "age": 35, "role": "manager"},
            ]
        }, indent=2)),
        "verify": lambda d: True,
    },

    # ── Level 2: 中等（多步操作） ──
    {
        "id": 4,
        "name": "创建+编辑+验证",
        "level": "medium",
        "instruction": (
            "1. Create a file called calc.py with a function add(a, b) that returns a + b\n"
            "2. Edit it to add a function multiply(a, b) that returns a * b\n"
            "3. Add a main block that tests both functions with add(2,3) and multiply(4,5)\n"
            "4. Run the file and confirm the output"
        ),
        "verify": lambda d: os.path.exists(os.path.join(d, "calc.py")),
    },
    {
        "id": 5,
        "name": "多文件项目创建",
        "level": "medium",
        "instruction": (
            "Create a small Python package:\n"
            "1. Create a directory called 'mylib'\n"
            "2. Create mylib/__init__.py that exports a 'version' variable set to '1.0.0'\n"
            "3. Create mylib/utils.py with functions: slugify(text) that converts text to lowercase-dashed format, "
            "and truncate(text, max_len=50) that truncates text with '...' if too long\n"
            "4. Create test_mylib.py that imports and tests both functions\n"
            "5. Run the tests"
        ),
        "verify": lambda d: (
            os.path.exists(os.path.join(d, "mylib", "__init__.py"))
            and os.path.exists(os.path.join(d, "mylib", "utils.py"))
            and os.path.exists(os.path.join(d, "test_mylib.py"))
        ),
    },
    {
        "id": 6,
        "name": "Bug 修复",
        "level": "medium",
        "instruction": (
            "The file buggy.py has a bug. Find and fix it, then run it to verify the fix.\n"
            "Expected output: the function should correctly calculate the average of a list of numbers."
        ),
        "setup": lambda d: Path(os.path.join(d, "buggy.py")).write_text(
            'def average(numbers):\n'
            '    """Calculate the average of a list of numbers."""\n'
            '    total = 0\n'
            '    for n in numbers:\n'
            '        total += n\n'
            '    return total / len(total)  # bug: should be len(numbers)\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    data = [10, 20, 30, 40, 50]\n'
            '    print(f"Average: {average(data)}")\n'
        ),
        "verify": lambda d: "len(numbers)" in Path(os.path.join(d, "buggy.py")).read_text(),
    },

    # ── Level 3: 复杂（多步 + 逻辑推理） ──
    {
        "id": 7,
        "name": "数据处理管道",
        "level": "complex",
        "instruction": (
            "Build a data processing pipeline:\n"
            "1. Read the CSV file sales.csv\n"
            "2. Create a Python script process.py that:\n"
            "   - Reads the CSV\n"
            "   - Calculates total revenue per product (quantity * price)\n"
            "   - Finds the top-selling product by revenue\n"
            "   - Writes a summary report to report.txt\n"
            "3. Run the script and show the report"
        ),
        "setup": lambda d: Path(os.path.join(d, "sales.csv")).write_text(
            "product,quantity,price\n"
            "Widget A,100,9.99\n"
            "Widget B,250,4.50\n"
            "Widget C,75,19.99\n"
            "Widget D,500,2.99\n"
            "Widget E,30,49.99\n"
        ),
        "verify": lambda d: (
            os.path.exists(os.path.join(d, "process.py"))
            and os.path.exists(os.path.join(d, "report.txt"))
        ),
    },
    {
        "id": 8,
        "name": "代码重构",
        "level": "complex",
        "instruction": (
            "Refactor the file legacy.py:\n"
            "1. Read and understand the current code\n"
            "2. Extract the repeated logic into reusable functions\n"
            "3. Add proper error handling\n"
            "4. Make sure the refactored code produces the same output as the original\n"
            "5. Run both versions and compare output"
        ),
        "setup": lambda d: Path(os.path.join(d, "legacy.py")).write_text(
            'import json\n'
            '\n'
            'data1 = \'{"name": "Alice", "scores": [85, 92, 78]}\'\n'
            'parsed1 = json.loads(data1)\n'
            'total1 = 0\n'
            'for s in parsed1["scores"]:\n'
            '    total1 += s\n'
            'avg1 = total1 / len(parsed1["scores"])\n'
            'print(f"{parsed1[\\"name\\"]}: avg={avg1:.1f}")\n'
            '\n'
            'data2 = \'{"name": "Bob", "scores": [90, 88, 95]}\'\n'
            'parsed2 = json.loads(data2)\n'
            'total2 = 0\n'
            'for s in parsed2["scores"]:\n'
            '    total2 += s\n'
            'avg2 = total2 / len(parsed2["scores"])\n'
            'print(f"{parsed2[\\"name\\"]}: avg={avg2:.1f}")\n'
            '\n'
            'data3 = \'{"name": "Charlie", "scores": [70, 75, 80]}\'\n'
            'parsed3 = json.loads(data3)\n'
            'total3 = 0\n'
            'for s in parsed3["scores"]:\n'
            '    total3 += s\n'
            'avg3 = total3 / len(parsed3["scores"])\n'
            'print(f"{parsed3[\\"name\\"]}: avg={avg3:.1f}")\n'
        ),
        "verify": lambda d: os.path.exists(os.path.join(d, "legacy.py")),
    },
    {
        "id": 9,
        "name": "REST API 服务器",
        "level": "complex",
        "instruction": (
            "Create a simple REST API server using only Python standard library:\n"
            "1. Create server.py with http.server that handles:\n"
            "   - GET /api/items → returns JSON list of items\n"
            "   - POST /api/items → adds an item, returns the new item\n"
            "   - GET /api/items/<id> → returns a single item\n"
            "2. Create test_api.py that uses urllib to test all 3 endpoints\n"
            "   (start server in a subprocess, run tests, then kill server)\n"
            "3. Run the tests"
        ),
        "verify": lambda d: (
            os.path.exists(os.path.join(d, "server.py"))
            and os.path.exists(os.path.join(d, "test_api.py"))
        ),
    },

    # ── Level 4: Skill 执行 ──
    {
        "id": 10,
        "name": "Skill: 专利法律状态查询",
        "level": "skill",
        "instruction": (
            "Execute the patent legal status query script located at "
            "{skill_dir}/patent-legal-status/scripts/legal_status.py "
            "with the patent number 'CN110245964A'. "
            "Report the legal status result."
        ),
        "verify": lambda d: True,
    },
    {
        "id": 11,
        "name": "Skill: 发现并执行脚本",
        "level": "skill",
        "instruction": (
            "1. List all files under {skill_dir}/patent-legal-status/\n"
            "2. Read the SKILL.md to understand what this skill does\n"
            "3. Read the script to understand its usage\n"
            "4. Execute the script with patent number 'CN110245964A'\n"
            "5. Summarize the result"
        ),
        "verify": lambda d: True,
    },

    # ── Level 5: 综合（端到端） ──
    {
        "id": 12,
        "name": "端到端: CLI 工具开发",
        "level": "e2e",
        "instruction": (
            "Build a complete CLI tool called 'wordcount':\n"
            "1. Create wordcount.py that accepts a file path as argument\n"
            "2. It should output: line count, word count, char count (like wc)\n"
            "3. Handle errors: file not found, permission denied, no arguments\n"
            "4. Create a sample text file sample.txt with 3 paragraphs of lorem ipsum\n"
            "5. Run wordcount.py on sample.txt and verify output\n"
            "6. Run wordcount.py with no arguments to verify error handling\n"
            "7. Run wordcount.py on a non-existent file to verify error handling"
        ),
        "verify": lambda d: (
            os.path.exists(os.path.join(d, "wordcount.py"))
            and os.path.exists(os.path.join(d, "sample.txt"))
        ),
    },
]


# ── 测试运行器 ────────────────────────────────────────────────

SKILL_DIR = str(Path(__file__).resolve().parent.parent / "skill")


def run_single_case(case: dict, agent_type: str, work_dir: str) -> dict:
    """运行单个测试用例"""

    # 替换 instruction 中的变量
    instruction = case["instruction"].replace("{skill_dir}", SKILL_DIR)

    # 执行 setup
    if "setup" in case:
        case["setup"](work_dir)

    t0 = time.time()

    if agent_type == "claude_api":
        agent = ClaudeAgent(work_dir=work_dir, max_turns=25)
        result = agent.run(instruction)
        elapsed = time.time() - t0
        return {
            "agent": "Claude API",
            "model": agent.model,
            "success": result.success,
            "elapsed": round(elapsed, 1),
            "turns": result.turns,
            "answer": result.answer[:500],
            "events": result.events,
            "verified": case["verify"](work_dir) if result.success else False,
        }
    elif agent_type == "claude_cli":
        agent = ClaudeCliAgent(work_dir=work_dir)
        result = agent.run(instruction, timeout=180)
        elapsed = time.time() - t0
        return {
            "agent": "Claude CLI",
            "model": "claude-code",
            "success": result.success,
            "elapsed": round(elapsed, 1),
            "turns": result.turns,
            "answer": result.answer[:500],
            "events": [],
            "cost": result.cost,
            "verified": case["verify"](work_dir) if result.success else False,
        }
    else:  # pi
        agent = PiAgent(work_dir=work_dir)
        result = agent.run(instruction, timeout=180)
        elapsed = time.time() - t0
        return {
            "agent": "Pi Agent",
            "model": agent.model,
            "success": result.success,
            "elapsed": round(elapsed, 1),
            "tool_calls": len(result.tool_calls),
            "answer": result.answer[:500],
            "events": result.events,
            "verified": case["verify"](work_dir) if result.success else False,
        }


def run_benchmark(case_ids: list[int] | None = None, agents: list[str] | None = None):
    """运行对比测试"""

    agent_list = agents or ALL_AGENTS
    cases = TEST_CASES
    if case_ids:
        cases = [c for c in TEST_CASES if c["id"] in case_ids]

    results = []

    for case in cases:
        print(f"\n{'#'*70}")
        print(f"# Case {case['id']}: {case['name']} [{case['level']}]")
        print(f"{'#'*70}")

        case_result = {
            "case_id": case["id"],
            "name": case["name"],
            "level": case["level"],
        }

        for agent_type in agent_list:
            label = {"pi": "Pi Agent", "claude_api": "Claude API", "claude_cli": "Claude CLI"}[agent_type]
            work = tempfile.mkdtemp(prefix=f"bench-{agent_type}-{case['id']}-")
            print(f"\n>>> {label} (work_dir={work})")
            try:
                case_result[agent_type] = run_single_case(case, agent_type, work)
            except Exception as e:
                case_result[agent_type] = {
                    "agent": label, "success": False, "elapsed": 0,
                    "error": str(e), "verified": False,
                }

        results.append(case_result)

    # ── 汇总报告 ──
    print_report(results, agent_list)
    save_report(results, agent_list)
    return results


def print_report(results: list[dict], agent_list: list[str]):
    """打印对比报告"""

    labels = {"pi": "Pi Agent", "claude_api": "Claude API", "claude_cli": "Claude CLI"}
    short = {"pi": "Pi", "claude_api": "API", "claude_cli": "CLI"}

    col_w = 14
    n_agents = len(agent_list)
    table_w = 4 + 24 + 8 + n_agents * col_w + col_w

    print(f"\n\n{'='*table_w}")
    print(f"{'BENCHMARK REPORT':^{table_w}}")
    print(f"{'='*table_w}")

    # Header
    header = f"  {'#':<4} {'Case':<24} {'Level':<8}"
    for a in agent_list:
        header += f" {labels[a]:>{col_w}}"
    header += f" {'Winner':>{col_w}}"
    print(header)
    print(f"{'─'*table_w}")

    wins = {a: 0 for a in agent_list}
    totals = {a: 0.0 for a in agent_list}

    for r in results:
        times = {}
        statuses = {}
        for a in agent_list:
            d = r.get(a, {})
            times[a] = d.get("elapsed", 0)
            totals[a] += times[a]
            if d.get("verified"):
                statuses[a] = "✓"
            elif d.get("success"):
                statuses[a] = "✗"
            else:
                statuses[a] = "ERR"

        # 判断赢家：先看成功，再看速度
        verified = {a for a in agent_list if statuses[a] == "✓"}
        winner = "Tie"
        if verified:
            fastest = min(verified, key=lambda a: times[a])
            # 只有在有明确速度差异时才判赢
            winner = short[fastest]
            wins[fastest] += 1

        row = f"  {r['case_id']:<4} {r['name']:<24} {r['level']:<8}"
        for a in agent_list:
            cell = f"{times[a]:>.1f}s {statuses[a]}"
            row += f" {cell:>{col_w}}"
        row += f" {winner:>{col_w}}"
        print(row)

    print(f"{'─'*table_w}")

    # Total row
    total_row = f"  {'TOTAL':<36}"
    for a in agent_list:
        cell = f"{totals[a]:>.1f}s"
        total_row += f" {cell:>{col_w}}"
    print(total_row)

    print(f"{'─'*table_w}")

    # Wins summary
    parts = [f"{labels[a]}: {wins[a]}" for a in agent_list]
    ties = len(results) - sum(wins.values())
    print(f"  Wins → {' | '.join(parts)} | Ties: {ties}")

    # Overall fastest
    fastest_agent = min(agent_list, key=lambda a: totals[a])
    print(f"  Overall fastest: {labels[fastest_agent]} ({totals[fastest_agent]:.1f}s total)")
    print(f"{'='*table_w}\n")


def save_report(results: list[dict], agent_list: list[str]):
    """保存详细报告到 JSON"""
    report_path = Path(__file__).parent / "benchmark_results.json"

    clean = []
    for r in results:
        cr = {
            "case_id": r["case_id"],
            "name": r["name"],
            "level": r["level"],
        }
        for a in agent_list:
            if a in r:
                cr[a] = {k: v for k, v in r[a].items() if k != "events"}
        clean.append(cr)

    report_path.write_text(json.dumps(clean, indent=2, ensure_ascii=False))
    print(f"[Report saved to {report_path}]")


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude API vs Claude CLI vs Pi Agent Benchmark")
    parser.add_argument("--case", type=str, help="Case IDs to run (e.g. '1,5,9')")
    parser.add_argument("--agents", type=str, default=",".join(ALL_AGENTS),
                        help="Agents to test (e.g. 'pi,claude_api,claude_cli')")
    parser.add_argument("--list", action="store_true", help="List all test cases")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'#':<4} {'Name':<30} {'Level':<10} Description")
        print(f"{'─'*80}")
        for c in TEST_CASES:
            print(f"{c['id']:<4} {c['name']:<30} {c['level']:<10} {c['instruction'][:60]}...")
        sys.exit(0)

    case_ids = None
    if args.case:
        case_ids = [int(x.strip()) for x in args.case.split(",")]

    agent_list = [a.strip() for a in args.agents.split(",")]
    run_benchmark(case_ids, agent_list)