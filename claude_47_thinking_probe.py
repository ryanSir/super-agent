#!/usr/bin/env python3
"""Probe Claude Opus 4.7 thinking through the gateway Anthropic endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


def load_environment() -> tuple[str, str]:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    api_base = os.getenv("OPENAI_API_BASE", "").strip().rstrip("/")
    if not api_key or not api_base:
        raise SystemExit("Missing OPENAI_API_KEY or OPENAI_API_BASE in .env/environment.")
    return api_key, api_base


def build_url(api_base: str) -> str:
    return f"{api_base.removesuffix('/v1')}/v1/messages"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Claude thinking via gateway Anthropic endpoint.")
    parser.add_argument("--model", default="claude-4.7-opus", help="Anthropic model name.")
    parser.add_argument("--effort", default="high", help="Thinking effort.")
    return parser.parse_args()


def extract_thinking_blocks(body: dict[str, Any]) -> list[dict[str, Any]]:
    content = body.get("content", [])
    blocks: list[dict[str, Any]] = []
    if not isinstance(content, list):
        return blocks
    for item in content:
        if isinstance(item, dict) and item.get("type") == "thinking":
            thinking_text = item.get("thinking", "")
            blocks.append(
                {
                    "thinking_len": len(thinking_text) if isinstance(thinking_text, str) else 0,
                    "thinking_preview": thinking_text[:200] if isinstance(thinking_text, str) else "",
                    "signature_present": bool(item.get("signature")),
                }
            )
    return blocks


def main() -> int:
    args = parse_args()
    api_key, api_base = load_environment()
    url = build_url(api_base)
    payload = {
        "model": args.model,
        "max_tokens": 1024,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": args.effort},
        "messages": [
            {
                "role": "user",
                "content": "请先思考，再简要回答：2026年大语言模型最新进展有哪些？",
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=payload)

    print(f"model={args.model}")
    print(f"status_code={response.status_code}")
    try:
        body = response.json()
    except Exception:
        print(response.text)
        return 1

    print(json.dumps(body, ensure_ascii=False, indent=2)[:4000])
    thinking_blocks = extract_thinking_blocks(body)
    print("\n=== thinking summary ===")
    print(json.dumps(thinking_blocks, ensure_ascii=False, indent=2))
    if response.is_error:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
