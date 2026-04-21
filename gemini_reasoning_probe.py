#!/usr/bin/env python3
"""Probe reasoning_content handling for OpenAI-compatible models via pydantic-ai."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta, ThinkingPartDelta
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.profiles.openai import OpenAIModelProfile, openai_model_profile
from pydantic_ai.providers.openai import OpenAIProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe reasoning_content streaming via pydantic-ai OpenAIModel.")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gateway model name.")
    parser.add_argument("--thinking", default="medium", help="Unified thinking level.")
    return parser.parse_args()


def load_environment() -> tuple[str, str]:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    api_base = os.getenv("OPENAI_API_BASE", "").strip()
    if not api_key or not api_base:
        raise SystemExit("Missing OPENAI_API_KEY or OPENAI_API_BASE in .env/environment.")
    return api_key, api_base


def build_model(model_name: str, api_key: str, api_base: str) -> OpenAIModel:
    provider = OpenAIProvider(api_key=api_key, base_url=api_base)
    profile = openai_model_profile(model_name).update(
        OpenAIModelProfile(
            openai_chat_thinking_field="reasoning_content",
            openai_chat_send_back_thinking_parts="field",
        )
    )
    return OpenAIModel(model_name, provider=provider, profile=profile)


async def main() -> int:
    args = parse_args()
    api_key, api_base = load_environment()
    model = build_model(args.model, api_key, api_base)
    agent = Agent(model)
    model_settings = OpenAIModelSettings(thinking=args.thinking, max_tokens=1024)

    async def handler(ctx: Any, events: Any) -> None:
        async for event in events:
            if isinstance(event, PartStartEvent):
                part = event.part
                print(
                    "PART_START",
                    {
                        "part_kind": getattr(part, "part_kind", ""),
                        "part_type": type(part).__name__,
                        "content_preview": str(getattr(part, "content", None))[:160],
                    },
                )
            elif isinstance(event, PartDeltaEvent):
                delta = event.delta
                preview = getattr(delta, "content_delta", None) or getattr(delta, "args_delta", None) or ""
                print(
                    "PART_DELTA",
                    {
                        "delta_type": type(delta).__name__,
                        "preview": str(preview)[:160],
                        "is_thinking": isinstance(delta, ThinkingPartDelta),
                        "is_text": isinstance(delta, TextPartDelta),
                    },
                )

    result = await agent.run(
        "请先认真思考，再简要回答：1+1等于几？",
        model_settings=model_settings,
        event_stream_handler=handler,
    )
    print("RESULT", result.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
