"""Subagent clarification demo using ask_parent.

This demonstrates parent/subagent communication with manual human input:
1. The parent starts a subagent task in async mode.
2. The subagent calls ask_parent() before making an assumption.
3. The parent sees WAITING_FOR_ANSWER via check_task().
4. The parent asks the human for an answer through ask_human().
5. The parent answers with answer_subagent().
6. The subagent continues and returns the clarified result.
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
from pydantic_ai import Agent, RunContext
from pydantic_deep import DeepAgentDeps, StateBackend, SubAgentConfig, create_deep_agent
from subagents_pydantic_ai.toolset import _create_ask_parent_toolset

from model_factory import create_model


EVENTS_CSV = """\
date,timestamp,user_id,event_type,value
2026-05-01,2026-05-01T08:15:00Z,u1,signup,1
2026-05-01,2026-05-01T09:20:00Z,u2,purchase,19.99
2026-05-02,2026-05-02T10:05:00Z,u1,purchase,29.99
2026-05-02,2026-05-02T11:30:00Z,u3,signup,1
2026-05-03,2026-05-03T12:00:00Z,u2,purchase,9.99
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


async def ask_human(ctx: RunContext[DeepAgentDeps], question: str) -> str:
    """Ask the human operator for a clarification answer."""
    prompt = f"\nSubagent asks:\n{question}\n\nYour answer: "
    return await asyncio.to_thread(input, prompt)


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    timeout_seconds = 240
    data_analyst_agent = Agent(
        create_model(model_name),
        instructions=(
            "You are a data analyst subagent. You have the ask_parent tool. "
            "If the task asks for daily time-series grouping and the input data "
            "has both 'date' and 'timestamp' columns, call ask_parent() before "
            "doing any analysis. After the parent answers, continue and return "
            "the final analysis."
        ),
        toolsets=[_create_ask_parent_toolset()],
    )

    subagents = [
        SubAgentConfig(
            name="data-analyst",
            description="Analyzes CSV data and asks for clarification when analysis choices are ambiguous.",
            agent=data_analyst_agent,
            can_ask_questions=True,
            max_questions=3,
            preferred_mode="async",
            typical_complexity="moderate",
        ),
    ]

    backend = StateBackend()
    deps = DeepAgentDeps(backend=backend)
    deps.backend.write("/data/events.csv", EVENTS_CSV)

    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are the parent orchestrator for a subagent clarification demo. "
            "When the data-analyst asks a question, inspect it with check_task, "
            "call ask_human with the question text, answer using answer_subagent "
            "with the human's answer, then wait for the final result."
        ),
        tools=[ask_human],
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
Demonstrate subagent clarification on /data/events.csv.

Required sequence:
1. Start data-analyst with task(..., mode="async"). Ask it to analyze daily purchase revenue and include this CSV content in the task description:

date,timestamp,user_id,event_type,value
2026-05-01,2026-05-01T08:15:00Z,u1,signup,1
2026-05-01,2026-05-01T09:20:00Z,u2,purchase,19.99
2026-05-02,2026-05-02T10:05:00Z,u1,purchase,29.99
2026-05-02,2026-05-02T11:30:00Z,u3,signup,1
2026-05-03,2026-05-03T12:00:00Z,u2,purchase,9.99

2. The data-analyst must ask which time column to use because the CSV has both date and timestamp.
3. Use check_task on the returned task_id until it shows waiting_for_answer and the question.
4. Call ask_human with the exact question returned by check_task.
5. Use the answer returned by ask_human as the answer_subagent(task_id, answer=...) value.
6. Use wait_tasks([task_id], timeout=180) to fetch the final clarified result.
7. Produce a short final summary that proves the subagent asked and then continued after the human answer.
"""

    print(f"model: {model_name}", flush=True)
    print(f"timeout: {timeout_seconds}s", flush=True)
    print("\n--- clarification events ---", flush=True)

    start = time.perf_counter()
    async with asyncio.timeout(timeout_seconds):
        async for event in agent.run_stream_events(prompt, deps=deps):
            print_event(event)
    elapsed = time.perf_counter() - start

    print(f"\n\nelapsed: {elapsed:.3f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())


# Use the timestamp column for time grouping; convert it to UTC dates.
