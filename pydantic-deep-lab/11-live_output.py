"""Live output demo using agent.iter().

This shows tool-specific progress messages when CallToolsNode appears.
"""

import asyncio
import time
from typing import Any

from pydantic_ai._agent_graph import CallToolsNode
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


INPUT_TEXT = """\
Project notes:
- Build a tiny fibonacci utility.
- Prefer an iterative implementation.
- Include one usage example.
"""


def tool_args(part: Any) -> dict[str, Any]:
    args = getattr(part, "args", {})
    if isinstance(args, dict):
        return args
    if hasattr(part, "args_as_dict"):
        try:
            return part.args_as_dict()
        except Exception:
            return {}
    return {}


async def run_with_live_output(agent, prompt: str, deps: DeepAgentDeps):
    async with agent.iter(prompt, deps=deps) as run:
        async for node in run:
            if isinstance(node, CallToolsNode):
                for part in node.model_response.parts:
                    if not hasattr(part, "tool_name"):
                        continue

                    tool = part.tool_name
                    args = tool_args(part)

                    if tool == "write_todos":
                        print("\nUpdated todo list", flush=True)
                    elif tool == "write_file":
                        path = args.get("path", "")
                        print(f"\nWriting: {path}", flush=True)
                    elif tool == "read_file":
                        path = args.get("path", "")
                        print(f"\nReading: {path}", flush=True)
                    else:
                        print(f"\nTool: {tool}", flush=True)

        return run.result


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    backend = StateBackend()
    backend.write("/notes/project.txt", INPUT_TEXT)

    agent = create_deep_agent(
        model=create_model(model_name),
        backend=backend,
        instructions=(
            "You are a concise coding assistant. Use tools when asked. "
            "For multi-step work, keep a short todo list."
        ),
        include_todo=True,
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
    deps = DeepAgentDeps(backend=backend)

    prompt = """
Read /notes/project.txt, then write /src/fibonacci.py with a small iterative
fibonacci function and one usage example. Use a todo list before editing.
"""

    print(f"model: {model_name}", flush=True)
    print("--- live output ---", flush=True)

    start = time.perf_counter()
    result = await run_with_live_output(agent, prompt, deps)
    elapsed = time.perf_counter() - start

    print(f"\nelapsed: {elapsed:.3f}s", flush=True)
    print(f"\nFinal output:\n{result.output}", flush=True)
    print("\nWritten file:", flush=True)
    print(backend.read("/src/fibonacci.py"), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
