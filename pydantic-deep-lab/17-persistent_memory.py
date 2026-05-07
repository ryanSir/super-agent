"""Persistent memory demo.

This verifies that create_deep_agent() enables memory by default:

1. Create an agent without passing include_memory.
2. Ask it to call write_memory.
3. Create a new agent instance with the same backend and memory_dir.
4. Show that the new agent can see the saved MEMORY.md content.
5. Ask it to call update_memory and print the persisted file.
"""

import asyncio
from pathlib import Path

from pydantic_deep import DeepAgentDeps, LocalBackend, create_deep_agent

from model_factory import create_model


WORKSPACE_DIR = Path(__file__).parent / "backend-workspace" / "persistent-memory"
MEMORY_DIR = ".deep/memory"
MEMORY_FILE = WORKSPACE_DIR / MEMORY_DIR / "main" / "MEMORY.md"


def create_memory_agent(model_name: str):
    return create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are a persistent-memory demo agent. "
            "When the user asks you to save or update memory, call the memory "
            "tool directly. Keep final answers short."
        ),
        # include_memory is intentionally omitted here. The default is True.
        memory_dir=MEMORY_DIR,
        include_todo=False,
        include_filesystem=False,
        include_subagents=False,
        include_skills=False,
        include_builtin_subagents=False,
        include_plan=False,
        context_manager=False,
        web_search=False,
        web_fetch=False,
        thinking=False,
        cost_tracking=False,
    )


def print_memory_file(label: str) -> None:
    print(f"\n[{label}]", flush=True)
    print(f"path: {MEMORY_FILE}", flush=True)
    if MEMORY_FILE.exists():
        print(MEMORY_FILE.read_text(encoding="utf-8"), flush=True)
    else:
        print("MEMORY.md does not exist yet.", flush=True)


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    backend = LocalBackend(root_dir=WORKSPACE_DIR, enable_execute=False)
    deps = DeepAgentDeps(backend=backend)

    print(f"model: {model_name}", flush=True)
    print("--- persistent memory demo ---", flush=True)
    print("include_memory: omitted, so create_deep_agent defaults it to True", flush=True)
    print_memory_file("before first run")

    first_agent = create_memory_agent(model_name)
    first = await first_agent.run(
        (
            "Call write_memory with exactly this content:\n"
            "- User prefers concise Chinese explanations for memory demos\n\n"
            "After the tool call, reply with only: saved."
        ),
        deps=deps,
    )

    print("\n[first run output]", flush=True)
    print(first.output, flush=True)
    print_memory_file("after write_memory")

    second_agent = create_memory_agent(model_name)
    second = await second_agent.run(
        (
            "From your injected Agent Memory, what user preference do you see? "
            "Do not call read_memory unless the memory is not visible."
        ),
        deps=deps,
    )

    print("\n[second agent output]", flush=True)
    print(second.output, flush=True)

    update = await second_agent.run(
        (
            "Call update_memory to replace exactly "
            "'concise Chinese explanations' with "
            "'concise bilingual explanations'. "
            "After the tool call, reply with only: updated."
        ),
        deps=deps,
    )

    print("\n[update output]", flush=True)
    print(update.output, flush=True)
    print_memory_file("after update_memory")


if __name__ == "__main__":
    asyncio.run(main())
