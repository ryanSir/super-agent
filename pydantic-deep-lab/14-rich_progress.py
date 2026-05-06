"""Rich progress demo using agent.iter().

This displays a spinner that changes as the agent thinks and calls tools.
"""

import asyncio
import time
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from model_factory import create_model


console = Console()


async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22 C"


def tool_names(node: CallToolsNode[Any, Any]) -> list[str]:
    tools = []
    for part in node.model_response.parts:
        if hasattr(part, "tool_name"):
            tools.append(part.tool_name)
    return tools


async def run_with_rich_progress(agent, prompt: str, deps: DeepAgentDeps):
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting...", total=None)

        async with agent.iter(prompt, deps=deps) as run:
            async for node in run:
                if isinstance(node, ModelRequestNode):
                    progress.update(task, description="Thinking...")
                elif isinstance(node, CallToolsNode):
                    tools = tool_names(node)
                    if tools:
                        progress.update(task, description=f"Tools: {', '.join(tools)}")

            progress.update(task, description="Complete!")
            return run.result


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

    console.print(f"model: {model_name}")

    start = time.perf_counter()
    result = await run_with_rich_progress(agent, "What is the weather in Shanghai?", deps)
    elapsed = time.perf_counter() - start

    console.print(f"\nelapsed: {elapsed:.3f}s")
    console.print(f"\nFinal output:\n{result.output}")


if __name__ == "__main__":
    asyncio.run(main())
