import asyncio
import time

from pydantic_ai import RunContext
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22 C"


async def main():
    model_name = "gateway-openai-gpt-5.4"
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

    start = time.perf_counter()
    result = await agent.run("What is the weather in Shanghai?", deps=deps)
    elapsed = time.perf_counter() - start

    print(f"model: {model_name}")
    print(f"elapsed: {elapsed:.3f}s")
    print(result.output)


asyncio.run(main())
