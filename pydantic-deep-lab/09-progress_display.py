"""Progress display demo using agent.iter().

This prints the current graph node on one terminal line while the agent runs.
"""

import asyncio
import sys
import time

from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


async def run_with_progress(agent, prompt: str, deps: DeepAgentDeps):
    step = 0

    async with agent.iter(prompt, deps=deps) as run:
        async for node in run:
            step += 1
            node_type = type(node).__name__
            sys.stdout.write(f"\r[Step {step}] {node_type}...")
            sys.stdout.flush()

        print("\n")
        return run.result


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

    start = time.perf_counter()
    result = await run_with_progress(
        agent,
        "Create a small Python function that calculates fibonacci numbers.",
        deps,
    )
    elapsed = time.perf_counter() - start

    print(f"elapsed: {elapsed:.3f}s", flush=True)
    print(f"\nFinal output:\n{result.output}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
