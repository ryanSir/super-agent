"""Agent Teams demo.

This demonstrates Teams as a flat multi-agent coordination layer:

1. The main agent creates a team with two members.
2. It assigns each member a background task.
3. It checks team/shared-task status and waits for the subagent tasks.
4. It dissolves the team.
"""

import asyncio
from typing import Any

from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
)
from pydantic_ai.run import AgentRunResultEvent
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent
from pydantic_deep.toolsets.teams import create_team_toolset
from subagents_pydantic_ai import DynamicAgentRegistry
from subagents_pydantic_ai.toolset import create_subagent_toolset

from model_factory import create_model


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
    registry = DynamicAgentRegistry()

    subagent_toolset = create_subagent_toolset(
        id="deep-subagents",
        subagents=None,
        default_model=create_model(model_name),
        include_general_purpose=False,
        registry=registry,
    )

    def team_agent_factory(config: dict[str, Any]):
        return create_deep_agent(
            model=create_model(model_name),
            instructions=(
                "You are a concise team member. "
                "Complete the assigned task directly.\n\n"
                f"{config.get('instructions') or ''}"
            ),
            include_todo=False,
            include_filesystem=False,
            include_subagents=False,
            include_skills=False,
            include_builtin_subagents=False,
            include_plan=False,
            include_memory=False,
            context_manager=False,
            web_search=False,
            web_fetch=False,
            thinking=False,
            cost_tracking=False,
        )

    team_toolset = create_team_toolset(
        registry=registry,
        agent_factory=team_agent_factory,
        task_fn=subagent_toolset.tools["task"].function,
        # Keep result collection on the subagent tools in this demo. In the
        # current local version, check_teammates expects enum task statuses
        # while TaskManager returns strings.
        task_manager=None,
    )

    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are a team lead. Use the team tools exactly as requested. "
            "Keep the final answer short."
        ),
        toolsets=[subagent_toolset, team_toolset],
        include_todo=False,
        include_filesystem=False,
        include_subagents=False,
        include_teams=False,
        include_skills=False,
        include_builtin_subagents=False,
        include_plan=False,
        include_memory=False,
        context_manager=False,
        web_search=False,
        web_fetch=False,
        thinking=False,
        cost_tracking=False,
    )
    deps = DeepAgentDeps(backend=StateBackend())

    print(f"model: {model_name}", flush=True)
    print("--- agent teams demo ---", flush=True)

    prompt = """
Demonstrate Agent Teams.

Required sequence:
1. Call spawn_team with team_name="learning-team" and exactly two members:
   - analyst: explains the difference between teams and subagents in one sentence.
   - reviewer: names one production risk of teams in one sentence.
2. Call assign_task for analyst.
3. Call assign_task for reviewer.
4. Call check_teammates.
5. Call list_active_tasks.
6. If task IDs are available, call wait_tasks with both task IDs and timeout=120.
7. Call check_teammates again.
8. Call dissolve_team.
9. Produce a short final summary using the wait_tasks results to prove the team members ran.
"""

    async for event in agent.run_stream_events(prompt, deps=deps):
        print_event(event)


if __name__ == "__main__":
    asyncio.run(main())
