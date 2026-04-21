#!/usr/bin/env python3
"""Inspect non-stream pydantic-ai result structure for reasoning_content models."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.profiles.openai import OpenAIModelProfile, openai_model_profile
from pydantic_ai.providers.openai import OpenAIProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--thinking", default="medium")
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


async def main() -> int:
    args = parse_args()
    api_key, api_base = load_environment()
    provider = OpenAIProvider(api_key=api_key, base_url=api_base)
    profile = openai_model_profile(args.model).update(
        OpenAIModelProfile(
            openai_chat_thinking_field="reasoning_content",
            openai_chat_send_back_thinking_parts="field",
        )
    )
    model = OpenAIModel(args.model, provider=provider, profile=profile)
    agent = Agent(model)
    result = await agent.run(
        "请先认真思考，再简要回答：1+1等于几？",
        model_settings=OpenAIModelSettings(thinking=args.thinking, max_tokens=1024),
    )
    print("OUTPUT:", result.output)
    messages = list(result.all_messages())
    print("MESSAGE_COUNT:", len(messages))
    for idx, msg in enumerate(messages[-3:]):
        print(f"\nMESSAGE[{idx}] {type(msg).__name__}")
        print("PROVIDER_DETAILS:", getattr(msg, "provider_details", None))
        parts = getattr(msg, "parts", None) or []
        for part in parts:
            print(
                "PART:",
                {
                    "type": type(part).__name__,
                    "kind": getattr(part, "part_kind", None),
                    "content": getattr(part, "content", None),
                    "id": getattr(part, "id", None),
                    "provider_name": getattr(part, "provider_name", None),
                    "provider_details": getattr(part, "provider_details", None),
                },
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
