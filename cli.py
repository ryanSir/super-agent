#!/usr/bin/env python3
"""DeepAgent CLI — 交互式命令行测试工具

直接调后端 API，实时显示 SSE 事件流。
用于验证各执行模式，无需启动前端。

用法：
  python cli.py                    # 交互模式
  python cli.py "1+1等于几"        # 单次查询
  python cli.py -m sub_agent "搜索论文并分析趋势"  # 指定模式
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from threading import Thread

BASE_URL = "http://localhost:9001"

# ANSI 颜色
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def submit_query(query: str, mode: str = "auto") -> dict:
    """提交查询"""
    data = json.dumps({"query": query, "mode": mode}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/agent/query",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"{RED}连接失败: {e}{RESET}")
        print(f"{DIM}确保后端已启动: python run_deepagent.py{RESET}")
        sys.exit(1)


def stream_events(session_id: str) -> None:
    """实时读取 SSE 事件流"""
    url = f"{BASE_URL}/api/agent/stream/{session_id}"
    try:
        resp = urllib.request.urlopen(url, timeout=300)
    except Exception as e:
        print(f"{RED}SSE 连接失败: {e}{RESET}")
        return

    answer_parts: list[str] = []
    start_time = time.monotonic()

    for raw_line in resp:
        line = raw_line.decode("utf-8", errors="replace").strip()

        if line.startswith("data:"):
            data_str = line[5:].strip()
            if not data_str:
                continue
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            event_type = event.get("event_type", "")
            _render_event(event_type, event, answer_parts, start_time)

            if event_type in ("session_completed", "session_failed"):
                break

    # 打印最终回答
    if answer_parts:
        print(f"\n{BOLD}{'─' * 60}{RESET}")
        print(f"{BOLD}最终回答:{RESET}")
        print("".join(answer_parts))

    elapsed = time.monotonic() - start_time
    print(f"\n{DIM}总耗时: {elapsed:.1f}s{RESET}")


def _render_event(
    event_type: str,
    event: dict,
    answer_parts: list[str],
    start_time: float,
) -> None:
    """渲染单个事件"""
    elapsed = time.monotonic() - start_time
    ts = f"{DIM}[{elapsed:6.1f}s]{RESET}"

    if event_type == "session_created":
        sid = event.get("session_id", "")
        print(f"{ts} {GREEN}● 会话创建{RESET} {DIM}{sid}{RESET}")

    elif event_type == "session_completed":
        answer = event.get("answer", "")
        if answer and not answer_parts:
            answer_parts.append(answer)
        print(f"{ts} {GREEN}✓ 会话完成{RESET}")

    elif event_type == "session_failed":
        error = event.get("error", "未知错误")
        print(f"{ts} {RED}✗ 会话失败: {error[:200]}{RESET}")

    elif event_type == "thinking":
        content = event.get("content", "")
        if content:
            print(f"{ts} {DIM}💭 {content[:100]}{RESET}")

    elif event_type == "step":
        title = event.get("title", "")
        status = event.get("status", "")
        icon = "⏳" if status == "running" else "✓" if status == "completed" else "✗"
        print(f"{ts} {CYAN}{icon} {title}{RESET}")

    elif event_type == "tool_call":
        tool_name = event.get("tool_name", "")
        args_preview = event.get("tool_args_preview", "")
        print(f"{ts} {YELLOW}🔧 {tool_name}{RESET} {DIM}{args_preview[:80]}{RESET}")

    elif event_type == "tool_result":
        tool_name = event.get("tool_name", "")
        result_preview = event.get("result_preview", "")
        print(f"{ts} {GREEN}📋 {tool_name} 返回{RESET} {DIM}{result_preview[:100]}{RESET}")

    elif event_type == "text_stream":
        delta = event.get("delta", "")
        if delta:
            answer_parts.append(delta)
            print(delta, end="", flush=True)

    elif event_type == "render_widget":
        component = event.get("ui_component", "")
        print(f"{ts} {CYAN}📊 渲染组件: {component}{RESET}")

    elif event_type == "sub_agent_started":
        name = event.get("sub_agent_name", "")
        task_id = event.get("task_id", "")
        print(f"{ts} {CYAN}🤖 Sub-Agent 启动: {name}{RESET} {DIM}{task_id}{RESET}")

    elif event_type == "sub_agent_completed":
        name = event.get("sub_agent_name", "")
        success = event.get("success", False)
        icon = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{ts} {icon} {CYAN}Sub-Agent 完成: {name}{RESET}")

    elif event_type == "heartbeat":
        pass  # 静默

    else:
        print(f"{ts} {DIM}[{event_type}]{RESET}")


def run_query(query: str, mode: str = "auto") -> None:
    """执行一次查询"""
    print(f"\n{BOLD}查询:{RESET} {query}")
    print(f"{DIM}模式: {mode}{RESET}")
    print(f"{'─' * 60}")

    result = submit_query(query, mode)
    if not result.get("success"):
        print(f"{RED}提交失败: {result.get('message', '')}{RESET}")
        return

    session_id = result["session_id"]
    trace_id = result.get("trace_id", "")
    print(f"{DIM}session: {session_id} | trace: {trace_id}{RESET}")
    print()

    stream_events(session_id)


def interactive_mode() -> None:
    """交互模式"""
    print(f"{BOLD}DeepAgent CLI{RESET} — 输入问题开始测试")
    print(f"{DIM}命令: /mode <direct|auto|plan_and_execute|sub_agent> 切换模式{RESET}")
    print(f"{DIM}命令: /quit 退出{RESET}")
    print()

    current_mode = "auto"

    while True:
        try:
            prompt = f"{CYAN}[{current_mode}]{RESET} > "
            query = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}再见{RESET}")
            break

        if not query:
            continue

        if query.startswith("/mode"):
            parts = query.split(maxsplit=1)
            if len(parts) > 1 and parts[1] in ("direct", "auto", "plan_and_execute", "sub_agent"):
                current_mode = parts[1]
                print(f"{GREEN}模式切换为: {current_mode}{RESET}")
            else:
                print(f"{YELLOW}可用模式: direct, auto, plan_and_execute, sub_agent{RESET}")
            continue

        if query in ("/quit", "/exit", "/q"):
            print(f"{DIM}再见{RESET}")
            break

        run_query(query, current_mode)
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepAgent CLI 测试工具")
    parser.add_argument("query", nargs="?", help="查询内容（不提供则进入交互模式）")
    parser.add_argument("-m", "--mode", default="auto",
                        choices=["direct", "auto", "plan_and_execute", "sub_agent"],
                        help="执行模式")
    parser.add_argument("--host", default="http://localhost:9001", help="后端地址")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.host

    if args.query:
        run_query(args.query, args.mode)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
