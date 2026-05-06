import asyncio

from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


async def main():
    agent = create_deep_agent(
        model=create_model("gateway-claude-sonnet-4.6"),
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

    result = await agent.run(
        "Create a Python function that calculates fibonacci numbers.",
        deps=deps,
    )

    print(result.output)


asyncio.run(main())
