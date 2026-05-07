"""Plan mode demo.

This demonstrates the plan-mode planner workflow:

1. A "planner" subagent is registered with create_plan_toolset().
2. The main agent delegates to the planner subagent via task.
3. The planner explores a small in-memory codebase.
4. The planner asks a clarifying question via ask_user.
5. The planner saves a markdown plan via save_plan.

The demo uses StateBackend so the planner can read and write files without
modifying the real workspace.
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
from pydantic_deep import DeepAgentDeps, StateBackend, SubAgentConfig, create_deep_agent
from pydantic_deep.toolsets.plan import (
    PLANNER_DESCRIPTION,
    PLANNER_INSTRUCTIONS,
    create_plan_toolset,
)

from model_factory import create_model


APP_CODE = """\
from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Demo API")
app.include_router(router)
"""

ROUTES_CODE = """\
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
"""

PYPROJECT = """\
[project]
name = "plan-mode-demo"
version = "0.1.0"
dependencies = [
    "fastapi",
    "uvicorn",
]
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


async def handle_ask_user(question: str, options: list[dict[str, str]]) -> str:
    """Headless ask_user callback that prints options and picks recommended."""
    print("\n[ask_user]", flush=True)
    print(question, flush=True)
    for index, option in enumerate(options, 1):
        recommended = " (recommended)" if option.get("recommended") == "true" else ""
        print(
            f"  {index}. {option['label']}{recommended}: {option['description']}",
            flush=True,
        )

    choice = next(
        (option for option in options if option.get("recommended") == "true"),
        options[0],
    )
    print(f"auto choice: {choice['label']}", flush=True)
    return choice["label"]


def create_planner_agent(model_name: str):
    """Create a planner subagent with the plan tools wired explicitly."""
    plan_toolset = create_plan_toolset(plans_dir="/plans")
    return create_deep_agent(
        model=create_model(model_name),
        instructions=PLANNER_INSTRUCTIONS,
        toolsets=[plan_toolset],
        include_todo=False,
        include_filesystem=True,
        include_execute=False,
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


def print_saved_plans(backend: StateBackend) -> None:
    plan_paths = sorted(path for path in backend.files if path.startswith("/plans/"))

    print("\n[saved plans]", flush=True)
    if not plan_paths:
        print("No plans saved.", flush=True)
        return

    for path in plan_paths:
        content = "\n".join(backend.files[path]["content"])
        print(f"\n--- {path} ---", flush=True)
        print(compact(content, max_len=4000), flush=True)


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    backend = StateBackend()
    backend.write("/app/main.py", APP_CODE)
    backend.write("/app/routes.py", ROUTES_CODE)
    backend.write("/pyproject.toml", PYPROJECT)

    deps = DeepAgentDeps(
        backend=backend,
        ask_user=handle_ask_user,
    )

    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are a plan-mode demo orchestrator. When asked to plan an "
            "implementation, delegate to the planner subagent using task. "
            "Do not edit files; only return the planner result."
        ),
        include_todo=False,
        include_filesystem=True,
        subagents=[
            SubAgentConfig(
                name="planner",
                description=PLANNER_DESCRIPTION,
                agent=create_planner_agent(model_name),
            )
        ],
        include_subagents=True,
        include_skills=False,
        include_builtin_subagents=False,
        # Current local pydantic-deep wires the built-in planner through the
        # default subagent factory, which does not pass cfg["toolsets"] into
        # the child agent. This demo registers the same planner explicitly so
        # ask_user and save_plan are definitely available.
        include_plan=False,
        include_memory=False,
        max_nesting_depth=1,
        context_manager=False,
        web_search=False,
        web_fetch=False,
        thinking=False,
        cost_tracking=False,
    )

    prompt = """
Use plan mode for this request.

Required sequence:
1. Delegate to the planner subagent with task(subagent_name="planner").
2. Ask the planner to inspect /app/main.py, /app/routes.py, and /pyproject.toml.
3. Ask the planner to use ask_user once to choose between JWT bearer auth,
   API key auth, or session cookies. Recommend JWT bearer auth.
4. Ask the planner to save a markdown implementation plan with save_plan.
5. After the planner returns, summarize where the plan was saved.

Planning target:
Add authentication to the demo FastAPI app without modifying files yet.
"""

    print(f"model: {model_name}", flush=True)
    print("--- plan mode demo ---", flush=True)

    async for event in agent.run_stream_events(prompt, deps=deps):
        print_event(event)

    print_saved_plans(backend)


if __name__ == "__main__":
    asyncio.run(main())
