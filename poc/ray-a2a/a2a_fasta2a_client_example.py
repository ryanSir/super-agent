"""A2A client example using fasta2a.client.A2AClient.

Start the server first:
    cd poc/ray-a2a
    uvicorn a2a_server:app --host 127.0.0.1 --port 8010

Then run from the repository root:
    python poc/ray-a2a/a2a_fasta2a_client_example.py
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fasta2a.client import A2AClient
from fasta2a.schema import Message, MessageSendConfiguration, TextPart


A2A_URL = "http://127.0.0.1:8010"
TERMINAL_STATES = {"completed", "failed", "canceled"}


def extract_text_output(task: dict[str, Any]) -> str:
    artifacts = task.get("artifacts", [])
    for artifact in artifacts:
        for part in artifact.get("parts", []):
            if part.get("kind") == "text":
                return part.get("text", "")
    return ""


async def call_remote_agent(text: str) -> str:
    client = A2AClient(base_url=A2A_URL)

    message = Message(
        role="user",
        parts=[TextPart(kind="text", text=text)],
        kind="message",
        message_id=f"msg-{uuid.uuid4().hex[:8]}",
    )
    configuration = MessageSendConfiguration(
        accepted_output_modes=["application/json"],
        history_length=10,
    )

    send_response = await client.send_message(message, configuration=configuration)
    if "error" in send_response:
        raise RuntimeError(f"A2A send failed: {send_response['error']}")

    task_id = send_response["result"]["id"]
    print("task id:", task_id)

    for _ in range(20):
        get_response = await client.get_task(task_id)
        if "error" in get_response:
            raise RuntimeError(f"A2A get task failed: {get_response['error']}")

        task = get_response["result"]
        state = task["status"]["state"]
        print("task state:", state)

        if state in TERMINAL_STATES:
            if state != "completed":
                raise RuntimeError(f"A2A task ended with state={state}: {task}")
            return extract_text_output(task)

        await asyncio.sleep(0.5)

    raise TimeoutError(f"A2A task did not finish: {task_id}")


async def main() -> None:
    output = await call_remote_agent("你好，这是 fasta2a client 发来的任务。")
    print("agent output:", output)


if __name__ == "__main__":
    asyncio.run(main())

