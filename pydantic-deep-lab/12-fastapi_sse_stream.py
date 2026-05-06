"""FastAPI SSE demo for streaming agent.iter() nodes.

Run:
    python pydantic-deep-lab/12-fastapi_sse_stream.py

Open:
    http://127.0.0.1:8012/agent/stream?prompt=What%20is%20the%20weather%20in%20Shanghai%3F
"""

from __future__ import annotations

import json
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic_ai import RunContext
from pydantic_ai._agent_graph import CallToolsNode
from pydantic_deep import DeepAgentDeps, StateBackend, create_deep_agent

from model_factory import create_model


MODEL_NAME = "gateway-claude-sonnet-4.6"


async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22 C"


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


def sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


app = FastAPI(title="Pydantic Deep Streaming Demo")

agent = create_deep_agent(
    model=create_model(MODEL_NAME),
    tools=[get_weather],
    instructions=(
        "You can check weather using tools. "
        "When the user asks about weather, call the weather tool."
    ),
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


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "stream": "/agent/stream?prompt=What%20is%20the%20weather%20in%20Shanghai%3F",
    }


@app.get("/agent/stream")
async def stream_agent(prompt: str = "What is the weather in Shanghai?") -> StreamingResponse:
    async def event_generator():
        deps = DeepAgentDeps(backend=StateBackend())
        yield sse_data({"type": "start", "model": MODEL_NAME, "prompt": prompt})

        try:
            async with agent.iter(prompt, deps=deps) as run:
                async for node in run:
                    node_type = type(node).__name__
                    data: dict[str, Any] = {"type": node_type}

                    if isinstance(node, CallToolsNode):
                        tools = []
                        for part in node.model_response.parts:
                            if hasattr(part, "tool_name"):
                                tools.append(
                                    {
                                        "name": part.tool_name,
                                        "args": tool_args(part),
                                    }
                                )
                        data["tools"] = tools

                    yield sse_data(data)

                yield sse_data({"type": "complete", "output": run.result.output})
        except Exception as exc:
            yield sse_data({"type": "error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8012)
