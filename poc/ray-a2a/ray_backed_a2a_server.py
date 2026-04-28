"""A2A server whose agent can call a Ray-backed tool.

Run:
    cd poc/ray-a2a
    uvicorn ray_backed_a2a_server:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

try:
    import ray
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "Missing dependency: ray. Install with `python -m pip install -r poc/ray-a2a/requirements.txt`."
    ) from exc

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel


@ray.remote
def summarize_with_ray(text: str) -> dict[str, object]:
    words = text.split()
    return {
        "word_count": len(words),
        "char_count": len(text),
        "preview": text[:80],
    }


if not ray.is_initialized():
    ray.init(ignore_reinit_error=True)

agent = Agent(
    TestModel(call_tools=["ray_summarize"], custom_output_text="Ray-backed tool completed."),
    instructions="Use ray_summarize when asked to analyze text.",
)


@agent.tool
async def ray_summarize(ctx: RunContext[None], text: str) -> dict[str, object]:
    del ctx
    ref = summarize_with_ray.remote(text)
    return ray.get(ref)


app = agent.to_a2a(
    name="super-agent-ray-a2a-poc",
    version="0.1.0",
    description="A2A server backed by a local Ray task.",
)

