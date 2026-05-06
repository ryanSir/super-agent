"""Async subagent demo: launch background tasks, then fetch results.

This demonstrates the async execution mode:
1. The orchestrator starts two independent subagent tasks with mode="async".
2. The task tool returns handles immediately.
3. The orchestrator checks active tasks and then waits for both results.
"""

import asyncio
import time
from typing import Any

from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
)
from pydantic_ai.run import AgentRunResultEvent
from pydantic_deep import DeepAgentDeps, StateBackend, SubAgentConfig, create_deep_agent

from model_factory import create_model


AUTH_CODE = """\
def authenticate(username, password):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    user = db.execute(query)
    if user and user.password == password:
        return True
    return False
"""


def compact(value: Any, max_len: int = 1200) -> str:
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n... <truncated>"


def print_event(event: Any) -> None:
    if isinstance(event, FunctionToolCallEvent):
        part = event.part
        print(f"\n\n[tool call] {part.tool_name}", flush=True)
        print(compact(part.args_as_dict()), flush=True)
        return

    if isinstance(event, FunctionToolResultEvent):
        result = event.result
        print(f"\n[tool result] {result.tool_name}", flush=True)
        print(compact(result.content), flush=True)
        return

    if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        print(event.delta.content_delta, end="", flush=True)
        return

    if isinstance(event, AgentRunResultEvent):
        print("\n\n[final output]", flush=True)
        print(event.result.output, flush=True)


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    timeout_seconds = 240

    subagents = [
        SubAgentConfig(
            name="code-reviewer",
            description="Reviews Python code for security and correctness issues.",
            model=create_model(model_name),
            preferred_mode="async",
            typical_complexity="complex",
            instructions=(
                "Review the requested Python code. Keep the review concise. "
                "Return findings with severity, evidence, and fixes."
            ),
        ),
        SubAgentConfig(
            name="test-planner",
            description="Plans focused pytest coverage for a Python function.",
            model=create_model(model_name),
            preferred_mode="async",
            typical_complexity="complex",
            instructions=(
                "Plan pytest coverage for the requested function. Keep the output concise. "
                "List happy paths, edge cases, and failure cases."
            ),
        ),
    ]

    backend = StateBackend()
    deps = DeepAgentDeps(backend=backend)
    deps.backend.write("/src/auth.py", AUTH_CODE)

    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are an orchestrator demonstrating async subagent execution. "
            "Follow the user's requested sequence exactly. Use async task handles, "
            "then explicitly retrieve the results before producing the final answer."
        ),
        subagents=subagents,
        include_todo=True,
        include_filesystem=True,
        include_subagents=True,
        include_skills=False,
        include_builtin_subagents=False,
        include_plan=False,
        include_memory=False,
        max_nesting_depth=0,
        context_manager=False,
        web_search=False,
        web_fetch=False,
        thinking=False,
        cost_tracking=False,
    )

    prompt = """
Demonstrate async subagent execution on /src/auth.py.

Required sequence:
1. Start code-reviewer with task(..., mode="async") to review /src/auth.py.
2. Start test-planner with task(..., mode="async") to plan pytest coverage for authenticate().
3. Use list_active_tasks to show both background tasks.
4. Use check_task for each returned task_id.
5. Use wait_tasks with both task_ids and timeout=180 to fetch both results.
6. Produce a short final summary that proves you waited for the async results.
"""

    print(f"model: {model_name}", flush=True)
    print(f"timeout: {timeout_seconds}s", flush=True)
    print("\n--- async task events ---", flush=True)

    start = time.perf_counter()
    async with asyncio.timeout(timeout_seconds):
        async for event in agent.run_stream_events(prompt, deps=deps):
            print_event(event)
    elapsed = time.perf_counter() - start

    print(f"\n\nelapsed: {elapsed:.3f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
