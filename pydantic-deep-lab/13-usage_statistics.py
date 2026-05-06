"""Usage statistics demo using agent.iter().

This prints token/request usage after a streamed run completes.
"""

import asyncio
import time

from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    agent = create_deep_agent(
        model=create_model(model_name),
        instructions="You are a helpful coding assistant. Be concise.",
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
    print("--- usage statistics ---", flush=True)

    start = time.perf_counter()
    async with agent.iter(
        "Create a small Python function that calculates fibonacci numbers.",
        deps=deps,
    ) as run:
        async for node in run:
            print(f"Node: {type(node).__name__}", flush=True)

        result = run.result
        usage = result.usage()

    elapsed = time.perf_counter() - start

    print(f"\nelapsed: {elapsed:.3f}s", flush=True)
    print(f"Input tokens: {usage.input_tokens}", flush=True)
    print(f"Output tokens: {usage.output_tokens}", flush=True)
    print(f"Total requests: {usage.requests}", flush=True)
    print(f"\nFinal output:\n{result.output}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
