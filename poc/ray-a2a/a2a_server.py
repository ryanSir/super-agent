"""Minimal Pydantic AI A2A server without external LLM credentials.

Run:
    cd poc/ray-a2a
    uvicorn a2a_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

agent = Agent(
    TestModel(custom_output_text="A2A PoC agent is reachable."),
    instructions="Return a deterministic response for A2A protocol smoke tests.",
)

app = agent.to_a2a(
    name="super-agent-a2a-poc",
    version="0.1.0",
    description="Minimal A2A server for validating Pydantic AI A2A exposure.",
)

