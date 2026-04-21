#!/usr/bin/env python3
"""Probe raw gateway responses for thinking/reasoning support."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

MODELS = [
    "gpt-5.4",
    "gpt-4o",
    "claude-4.6-opus",
    "claude-4.6-sonnet",
    "deepseek-r1",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash",
    "qwen3.5-plus",
    "kimi-k2.5",
]

THINKING_KEY_RE = re.compile(r"(reasoning|thinking)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe reasoning/thinking support through rd-gateway.")
    parser.add_argument("--model", action="append", help="Model name. Repeat or use comma-separated values.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument("--output-json", required=True, help="Output JSON file path.")
    return parser.parse_args()


def parse_models(values: list[str] | None) -> list[str]:
    if not values:
        return list(MODELS)
    parsed: list[str] = []
    for value in values:
        parsed.extend(part.strip() for part in value.split(",") if part.strip())
    return parsed


def find_dotenv_file() -> Path | None:
    search_roots = [Path.cwd(), Path(__file__).resolve().parent]
    seen: set[Path] = set()
    for root in search_roots:
        for candidate in [root, *root.parents]:
            if candidate in seen:
                continue
            seen.add(candidate)
            env_path = candidate / ".env"
            if env_path.exists():
                return env_path
    return None


def load_environment() -> tuple[str, str]:
    env_file = find_dotenv_file()
    if env_file:
        load_dotenv(env_file, override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    api_base = os.getenv("OPENAI_API_BASE", "").strip().rstrip("/")
    if not api_key or not api_base:
        raise SystemExit("Missing OPENAI_API_KEY or OPENAI_API_BASE in environment/.env.")
    return api_key, api_base


def extract_sse_data(line: str) -> str | None:
    if line.startswith("data:"):
        return line[5:].lstrip()
    return None


def summarize_reasoning(observed: list[dict[str, Any]]) -> tuple[str, list[str]]:
    if not observed:
        return "absent", []
    content_items = [item for item in observed if item["kind"] == "content"]
    metadata_items = [item for item in observed if item["kind"] == "metadata"]
    evidence = [f"{item['path']}={item['value_preview']}" for item in observed[:8]]
    if content_items:
        return "content_exposed", evidence
    if metadata_items:
        return "metadata_only", evidence
    return "placeholder_only", evidence


def walk_for_reasoning(value: Any, path: str = "$") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if THINKING_KEY_RE.search(key):
                preview = json.dumps(child, ensure_ascii=False)[:120]
                if "token" in key.lower() or "token" in child_path.lower():
                    kind = "metadata"
                elif child not in (None, "", [], {}, False):
                    kind = "content"
                else:
                    kind = "placeholder"
                found.append(
                    {
                        "path": child_path,
                        "non_empty": child not in (None, "", [], {}, False),
                        "kind": kind,
                        "value_preview": preview,
                    }
                )
            found.extend(walk_for_reasoning(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(walk_for_reasoning(child, f"{path}[{index}]"))
    return found


def probe_non_stream(client: httpx.Client, api_key: str, api_base: str, model: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "请认真思考后回答：37乘以19等于多少？只输出最终答案。",
            }
        ],
        "max_tokens": 256,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    try:
        response = client.post(f"{api_base}/chat/completions", headers=headers, json=payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        body = response.json()
        response.raise_for_status()
        choices = body.get("choices", [])
        content = ""
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "") if isinstance(message, dict) else ""
        reasoning_hits = walk_for_reasoning(body)
        reasoning_status, evidence = summarize_reasoning(reasoning_hits)
        return {
            "request_ok": True,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "content_non_empty": bool(content),
            "reasoning_support": reasoning_status,
            "reasoning_evidence": evidence,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return {
            "request_ok": False,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "content_non_empty": False,
            "reasoning_support": "error",
            "reasoning_evidence": [],
            "error": str(exc),
        }


def probe_stream(client: httpx.Client, api_key: str, api_base: str, model: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "请认真思考后回答：37乘以19等于多少？只输出最终答案。",
            }
        ],
        "max_tokens": 256,
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    chunk_count = 0
    content_parts: list[str] = []
    reasoning_hits: list[dict[str, Any]] = []
    finish_reason_present = False
    try:
        with client.stream("POST", f"{api_base}/chat/completions", headers=headers, json=payload) as response:
            status_code = response.status_code
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                data = extract_sse_data(raw_line)
                if data is None:
                    continue
                if data == "[DONE]":
                    break
                event = json.loads(data)
                chunk_count += 1
                reasoning_hits.extend(walk_for_reasoning(event))
                choices = event.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if isinstance(content, str):
                        content_parts.append(content)
                    if choices[0].get("finish_reason") is not None:
                        finish_reason_present = True
        latency_ms = int((time.perf_counter() - started) * 1000)
        reasoning_status, evidence = summarize_reasoning(reasoning_hits)
        return {
            "request_ok": True,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "chunk_received": chunk_count > 0,
            "finish_reason_present": finish_reason_present,
            "content_reconstructed": bool("".join(content_parts).strip()),
            "reasoning_support": reasoning_status,
            "reasoning_evidence": evidence,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return {
            "request_ok": False,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "chunk_received": False,
            "finish_reason_present": False,
            "content_reconstructed": False,
            "reasoning_support": "error",
            "reasoning_evidence": [],
            "error": str(exc),
        }


def main() -> int:
    args = parse_args()
    models = parse_models(args.model)
    api_key, api_base = load_environment()
    results: dict[str, Any] = {}
    with httpx.Client(timeout=args.timeout) as client:
        for model in models:
            results[model] = {
                "non_stream": probe_non_stream(client, api_key, api_base, model),
                "stream": probe_stream(client, api_key, api_base, model),
            }
            print(
                f"{model}: non_stream={results[model]['non_stream']['reasoning_support']} "
                f"stream={results[model]['stream']['reasoning_support']}"
            )
    output_path = Path(args.output_json)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
