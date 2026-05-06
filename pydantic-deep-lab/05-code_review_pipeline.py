"""Code review demo using an isolated subagent context.

The orchestrator delegates review work to one subagent. The subagent shares the
same backend/files so it can read `/src/auth.py`, but it gets its own todo/context
through `clone_for_subagent()`.
"""

import asyncio
import time

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


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    timeout_seconds = 180

    subagents = [
        SubAgentConfig(
            name="code-reviewer",
            description="Reviews code for correctness, security, performance, and style issues.",
            model=create_model(model_name),
            instructions=(
                "Review code thoroughly. Check for security issues, performance "
                "problems, error handling gaps, and code style problems. Format "
                "your review as markdown with clear sections and actionable findings."
            ),
        ),
    ]

    backend = StateBackend()
    deps = DeepAgentDeps(backend=backend)
    deps.backend.write("/src/auth.py", AUTH_CODE)

    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are an orchestrator for a code review pipeline. Delegate code "
            "review work to code-reviewer, then return the subagent's findings "
            "as a concise markdown report."
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
1. Review /src/auth.py for security issues.
2. Report findings with severity, evidence, and concrete fixes.
"""

    print(f"model: {model_name}", flush=True)
    print(f"timeout: {timeout_seconds}s", flush=True)
    print("\n--- streamed review ---\n", flush=True)

    start = time.perf_counter()
    async with asyncio.timeout(timeout_seconds):
        async with agent.run_stream(prompt, deps=deps) as response:
            async for delta in response.stream_text(delta=True, debounce_by=None):
                print(delta, end="", flush=True)
    elapsed = time.perf_counter() - start

    print(f"\n\nelapsed: {elapsed:.3f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
