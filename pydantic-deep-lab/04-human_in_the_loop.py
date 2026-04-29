"""Human-in-the-loop demo for deferred tool approval.

This example asks the agent to run a shell command that writes a file, pauses
before `execute`, asks the human to approve or deny it, then resumes with that
decision. If approved, the workspace gets an `approval-output.txt` file.
"""

import asyncio
from pathlib import Path
from typing import Any

from pydantic_ai.tools import DeferredToolRequests, DeferredToolResults, ToolApproved, ToolDenied
from pydantic_deep import DeepAgentDeps, LocalBackend, create_deep_agent

from model_factory import create_model


def get_deferred_requests(output: Any) -> DeferredToolRequests | None:
    if isinstance(output, DeferredToolRequests):
        return output
    return None


def ask_human_approval(tool_name: str, args: Any) -> ToolApproved | ToolDenied:
    print(f"- tool={tool_name}")
    print(f"  args={args}")

    while True:
        decision = input("Approve this tool call? [y/n]: ").strip().lower()
        if decision in {"y", "yes"}:
            return ToolApproved()
        if decision in {"n", "no"}:
            reason = input("Reason for denial: ").strip() or "Denied by human reviewer."
            return ToolDenied(reason)
        print("Please enter y or n.")


async def main() -> None:
    model_name = "gateway-openai-gpt-5.4"
    workspace = Path(__file__).parent / "backend-workspace" / "human-in-the-loop"
    backend = LocalBackend(root_dir=workspace)

    agent = create_deep_agent(
        model=create_model(model_name),
        backend=backend,
        include_execute=True,
        interrupt_on={"execute": True},
        instructions=(
            "You are a concise coding assistant. "
            "When asked to run a command in this demo, use the execute tool once."
        ),
        include_todo=False,
        include_filesystem=True,
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

    command = (
        "python -c \"from pathlib import Path; "
        "Path('approval-output.txt').write_text('Created after human approval.\\n'); "
        "print('wrote approval-output.txt')\""
    )

    result = await agent.run(f"Run this exact command: {command}", deps=deps)

    deferred = get_deferred_requests(result.output)
    if deferred is None:
        print("No approval was requested.")
        print(result.output)
        return

    print("Approval needed:")
    approvals = {}
    for call in deferred.approvals:
        print(f"\nPending approval id={call.tool_call_id} name={call.tool_name}")
        approvals[call.tool_call_id] = ask_human_approval(call.tool_name, call.args)

    resumed = await agent.run(
        deps=deps,
        message_history=result.all_messages(),
        deferred_tool_results=DeferredToolResults(approvals=approvals),
    )

    print("\nFinal output:")
    print(resumed.output)

    output_file = workspace / "approval-output.txt"
    if output_file.exists():
        print("\nWorkspace file:")
        print(output_file)
        print(output_file.read_text())


if __name__ == "__main__":
    asyncio.run(main())
