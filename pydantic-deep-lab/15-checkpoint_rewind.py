"""Checkpoint rewind demo.

This shows the application-level part of checkpoint rewind:

1. Create a clean starting checkpoint.
2. Add a later fact to the conversation.
3. Ask the agent to call rewind_to(checkpoint_id).
4. Catch RewindRequested and replace message_history with e.messages.
"""

import asyncio

from pydantic_deep import (
    DeepAgentDeps,
    InMemoryCheckpointStore,
    RewindRequested,
    StateBackend,
    create_deep_agent,
)

from model_factory import create_model


async def print_checkpoints(store: InMemoryCheckpointStore) -> str:
    checkpoints = await store.list_all()
    print("\nSaved checkpoints:", flush=True)
    for checkpoint in checkpoints:
        print(
            f"- label={checkpoint.label!r}, id={checkpoint.id}, "
            f"messages={checkpoint.message_count}",
            flush=True,
        )

    if not checkpoints:
        raise RuntimeError("No checkpoints were saved.")

    return checkpoints[0].id


async def main() -> None:
    model_name = "gateway-claude-sonnet-4.6"
    store = InMemoryCheckpointStore()
    agent = create_deep_agent(
        model=create_model(model_name),
        instructions=(
            "You are a checkpointing demo agent. "
            "If the user asks you to rewind and gives a checkpoint_id, "
            "call the rewind_to tool with exactly that checkpoint_id."
        ),
        include_checkpoints=True,
        checkpoint_store=store,
        checkpoint_frequency="every_turn",
        max_checkpoints=10,
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
    print("--- checkpoint rewind demo ---", flush=True)

    message_history = []

    clean = await agent.run(
        "This is a clean starting point. Reply with only: ready.",
        deps=deps,
        message_history=message_history,
    )
    message_history = clean.all_messages()

    print("\n[clean checkpoint output]", flush=True)
    print(clean.output, flush=True)
    print(f"message_history length after clean run: {len(message_history)}", flush=True)

    clean_checkpoint_id = await print_checkpoints(store)

    later = await agent.run(
        "Remember this fact: the project codename is Atlas. Reply briefly.",
        deps=deps,
        message_history=message_history,
    )
    message_history = later.all_messages()

    print("\n[later output]", flush=True)
    print(later.output, flush=True)
    print(f"message_history length after later run: {len(message_history)}", flush=True)

    try:
        await agent.run(
            (
                "Rewind the conversation back to the clean checkpoint now. "
                f"Use checkpoint_id={clean_checkpoint_id}. "
                "Do not just describe rewinding; call the tool."
            ),
            deps=deps,
            message_history=message_history,
        )
    except RewindRequested as exc:
        print("\n[rewind requested]", flush=True)
        print(f"label: {exc.label}", flush=True)
        print(f"checkpoint_id: {exc.checkpoint_id}", flush=True)
        print(f"messages restored from checkpoint: {len(exc.messages)}", flush=True)

        message_history = exc.messages
        print(
            f"message_history length after application restore: {len(message_history)}",
            flush=True,
        )

    follow_up = await agent.run(
        "What project codename do you remember? If none is present, say: none.",
        deps=deps,
        message_history=message_history,
    )

    print("\n[follow-up after rewind]", flush=True)
    print(follow_up.output, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
