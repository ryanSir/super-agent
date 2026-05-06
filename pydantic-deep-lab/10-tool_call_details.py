"""Tool call details demo using agent.iter().

This prints tool call names and arguments from CallToolsNode.
"""

import asyncio
import time
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai._agent_graph import CallToolsNode
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22 C"


def print_tool_call_details(node: CallToolsNode[Any, Any]) -> None:
    for part in node.model_response.parts:
        if hasattr(part, "tool_name"):
            print(f"Tool: {part.tool_name}", flush=True)
            if hasattr(part, "args"):
                print(f"  Args: {part.args}", flush=True)


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    agent = create_deep_agent(
        model=create_model(model_name),
        tools=[get_weather],
        instructions=(
            "You can check weather using tools. "
            "When the user asks about weather, call the weather tool."
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
    deps = DeepAgentDeps(backend=StateBackend())

    print(f"model: {model_name}", flush=True)
    print("--- tool call details ---", flush=True)

    start = time.perf_counter()
    async with agent.iter("What is the weather in Shanghai?", deps=deps) as run:
        async for node in run:
            print(f"Node: {type(node).__name__}", flush=True)
            if isinstance(node, CallToolsNode):
                print_tool_call_details(node)

        result = run.result

    elapsed = time.perf_counter() - start

    print(f"\nelapsed: {elapsed:.3f}s", flush=True)
    print(f"\nFinal output:\n{result.output}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
