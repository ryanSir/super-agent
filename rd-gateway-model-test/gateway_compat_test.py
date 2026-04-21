#!/usr/bin/env python3
"""RD-Gateway multi-model compatibility test runner.

Strategy:
- All models default to the OpenAI-compatible `/v1/chat/completions` path.
- Claude models retry the failed dimension through Anthropic native `/v1/messages`.
- Output per-dimension checks plus a final compatibility matrix.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import anthropic
import httpx
import jsonschema
from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODELS = [
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

DEFAULT_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
ANTHROPIC_VERSION = "2023-06-01"


class Status(str, Enum):
    PASS = "PASS"
    PASS_FALLBACK = "PASS_FALLBACK"
    PASS_SSE_COMPAT = "PASS_SSE_COMPAT"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    vendor: str
    supports_fallback: bool = False


@dataclass
class DimensionResult:
    dimension: str
    status: Status
    path: str
    latency_ms: int
    checks: dict[str, bool] = field(default_factory=dict)
    error: str | None = None
    notes: list[str] = field(default_factory=list)


MODEL_SPECS = {
    "gpt-5.4": ModelSpec("gpt-5.4", "OpenAI"),
    "gpt-4o": ModelSpec("gpt-4o", "OpenAI"),
    "claude-4.6-opus": ModelSpec("claude-4.6-opus", "Anthropic", supports_fallback=True),
    "claude-4.6-sonnet": ModelSpec("claude-4.6-sonnet", "Anthropic", supports_fallback=True),
    "claude-4.7-opus": ModelSpec("claude-4.7-opus", "Anthropic", supports_fallback=True),
    "deepseek-r1": ModelSpec("deepseek-r1", "DeepSeek"),
    "gemini-3.1-pro-preview": ModelSpec("gemini-3.1-pro-preview", "Google"),
    "gemini-2.5-flash": ModelSpec("gemini-2.5-flash", "Google"),
    "qwen3.5-plus": ModelSpec("qwen3.5-plus", "Alibaba"),
    "kimi-k2.5": ModelSpec("kimi-k2.5", "Moonshot"),
    "doubao-seed-2.0-pro": ModelSpec("doubao-seed-2.0-pro", "ByteDance"),
    "glm-5.1": ModelSpec("glm-5.1", "Zhipu"),
    "glm-5": ModelSpec("glm-5", "Zhipu"),
    "minimax-2.7": ModelSpec("minimax-2.7", "MiniMax"),
}


WEATHER_TOOL_OAI = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name in Chinese or English.",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}

TIME_TOOL_OAI = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "Get the current local time for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name in Chinese or English.",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}

COMPLEX_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "channel": {
            "type": "string",
            "enum": ["email", "sms", "webhook"],
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "target": {
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "region": {"type": "string"},
            },
            "required": ["team", "region"],
            "additionalProperties": False,
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
        },
    },
    "required": ["channel", "priority", "target", "tags"],
    "additionalProperties": False,
}

COMPLEX_TOOL_OAI = {
    "type": "function",
    "function": {
        "name": "create_alert",
        "description": "Create an alert routing configuration.",
        "parameters": COMPLEX_TOOL_SCHEMA,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RD-Gateway model compatibility tests.")
    parser.add_argument(
        "--model",
        action="append",
        help="Model name. Repeat or pass comma-separated values. Default: all configured models.",
    )
    parser.add_argument(
        "--dim",
        action="append",
        help="Dimension id, e.g. D3. Repeat or pass comma-separated values. Default: D1-D7.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds. Default: 60.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Max tokens for each request. Default: 256.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to write structured results as JSON.",
    )
    parser.add_argument(
        "--path",
        choices=["openai", "anthropic"],
        default="openai",
        help="API path to use. 'openai' = /v1/chat/completions, 'anthropic' = /v1/messages. Default: openai.",
    )
    return parser.parse_args()


def parse_csv_args(values: list[str] | None, default: list[str]) -> list[str]:
    if not values:
        return list(default)
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
    api_base = os.getenv("OPENAI_API_BASE", "").strip()
    if not api_key or not api_base:
        raise SystemExit("Missing OPENAI_API_KEY or OPENAI_API_BASE in environment/.env.")
    return api_key, api_base.rstrip("/")


def derive_gateway_root(api_base: str) -> str:
    parsed = urlparse(api_base)
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[: -len("/chat/completions")]
    if path.endswith("/v1"):
        path = path[: -len("/v1")]
    return parsed._replace(path=path or "", params="", query="", fragment="").geturl().rstrip("/")


def anthropic_tool_from_openai(tool: dict[str, Any]) -> dict[str, Any]:
    fn = tool["function"]
    return {
        "name": fn["name"],
        "description": fn.get("description", ""),
        "input_schema": fn["parameters"],
    }


def compute_status(checks: dict[str, bool], error: str | None) -> Status:
    if error:
        return Status.FAIL
    if checks and all(checks.values()):
        return Status.PASS
    if checks and any(checks.values()):
        return Status.PARTIAL
    return Status.FAIL


def now_ms() -> int:
    return int(time.perf_counter() * 1000)


def extract_text_from_openai_message(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts).strip()
    return ""


def flatten_anthropic_text(content: list[Any]) -> str:
    texts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            texts.append(getattr(block, "text", ""))
        elif isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text", "")))
    return "".join(texts).strip()


def first_anthropic_tool_uses(content: list[Any]) -> list[Any]:
    tool_uses: list[Any] = []
    for block in content:
        block_type = getattr(block, "type", None) if not isinstance(block, dict) else block.get("type")
        if block_type == "tool_use":
            tool_uses.append(block)
    return tool_uses


class OpenAICompatRunner:
    def __init__(self, api_key: str, api_base: str, timeout: float, max_tokens: int) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key, base_url=self.api_base, timeout=timeout)

    def _chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=self.max_tokens,
            **kwargs,
        )

    def run_d1(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._chat(
                model,
                [{"role": "user", "content": "请只回复 OK，不要加解释。"}],
            )
            choice = response.choices[0]
            content = extract_text_from_openai_message(choice.message)
            checks = {
                "has_choice": bool(response.choices),
                "role_assistant": getattr(choice.message, "role", None) == "assistant",
                "content_non_empty": bool(content),
                "finish_reason_stop": choice.finish_reason == "stop",
            }
            if content:
                notes.append(f"content={content[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D1", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d2(self, model: str, lenient_sse: bool = False) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "请用一句中文短句介绍今天的天气。"}],
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        text_parts: list[str] = []
        saw_delta = False
        finish_reason: str | None = None
        chunk_count = 0
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines():
                        if not raw_line:
                            continue
                        if lenient_sse:
                            if not raw_line.startswith("data"):
                                continue
                            data = raw_line[len("data:"):].lstrip()
                        else:
                            if not raw_line.startswith("data: "):
                                continue
                            data = raw_line[6:]
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        chunk_count += 1
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if delta:
                            saw_delta = True
                        content = delta.get("content")
                        if isinstance(content, str):
                            text_parts.append(content)
                        finish_reason = choices[0].get("finish_reason") or finish_reason
            full_text = "".join(text_parts).strip()
            checks = {
                "chunk_received": chunk_count > 0,
                "delta_present": saw_delta,
                "finish_reason_present": finish_reason is not None,
                "content_reconstructed": bool(full_text),
            }
            if full_text:
                notes.append(f"stream_text={full_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D2", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d3(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._chat(
                model,
                [
                    {
                        "role": "user",
                        "content": "你必须调用 get_weather 工具查询北京天气，不要直接回答。",
                    }
                ],
                tools=[WEATHER_TOOL_OAI],
                tool_choice="auto",
            )
            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None) or []
            tool_name = tool_calls[0].function.name if tool_calls else None
            args = tool_calls[0].function.arguments if tool_calls else ""
            checks = {
                "tool_calls_present": bool(tool_calls),
                "tool_name_match": tool_name == "get_weather",
                "arguments_valid_json": is_valid_json(args),
                "finish_reason_tool_calls": choice.finish_reason == "tool_calls",
            }
            if args:
                notes.append(f"args={args}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D3", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d4(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._chat(
                model,
                [
                    {
                        "role": "user",
                        "content": "请同时调用 get_weather 和 get_time 查询北京天气和现在几点，不要直接回答。",
                    }
                ],
                tools=[WEATHER_TOOL_OAI, TIME_TOOL_OAI],
                tool_choice="auto",
                parallel_tool_calls=True,
            )
            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None) or []
            tool_ids = [call.id for call in tool_calls]
            tool_names = [call.function.name for call in tool_calls]
            valid_args = all(is_valid_json(call.function.arguments) for call in tool_calls)
            checks = {
                "at_least_two_tools": len(tool_calls) >= 2,
                "distinct_tool_ids": len(set(tool_ids)) == len(tool_ids) and bool(tool_ids),
                "expected_tool_names": {"get_weather", "get_time"}.issubset(set(tool_names)),
                "all_arguments_valid_json": valid_args,
            }
            if tool_names:
                notes.append(f"tool_names={','.join(tool_names)}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D4", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d5(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            first = self._chat(
                model,
                [
                    {
                        "role": "user",
                        "content": "请调用 get_weather 查询北京天气，拿到结果后再给我一句总结。",
                    }
                ],
                tools=[WEATHER_TOOL_OAI],
                tool_choice="auto",
            )
            choice = first.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None) or []
            if not tool_calls:
                checks = {
                    "first_turn_tool_call": False,
                    "second_turn_text": False,
                    "references_tool_result": False,
                }
            else:
                tool_call = tool_calls[0]
                messages = [
                    {"role": "user", "content": "请调用 get_weather 查询北京天气，拿到结果后再给我一句总结。"},
                    {
                        "role": "assistant",
                        "content": choice.message.content or "",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                        ],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "北京天气晴，22C，东北风2级。",
                    },
                ]
                second = self._chat(model, messages, tools=[WEATHER_TOOL_OAI], tool_choice="auto")
                second_choice = second.choices[0]
                second_text = extract_text_from_openai_message(second_choice.message)
                second_tool_calls = getattr(second_choice.message, "tool_calls", None) or []
                checks = {
                    "first_turn_tool_call": True,
                    "second_turn_text": bool(second_text) and not second_tool_calls,
                    "references_tool_result": any(token in second_text for token in ["22", "晴", "东北风"]),
                }
                if second_text:
                    notes.append(f"roundtrip_text={second_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D5", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d6(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._chat(
                model,
                [
                    {
                        "role": "user",
                        "content": (
                            "请调用 create_alert，参数要求：channel=email，priority=high，"
                            "team=platform，region=cn，tags 至少包含 gateway 和 urgent。不要直接回答。"
                        ),
                    }
                ],
                tools=[COMPLEX_TOOL_OAI],
                tool_choice="auto",
            )
            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None) or []
            args_raw = tool_calls[0].function.arguments if tool_calls else ""
            parsed = json.loads(args_raw) if args_raw else None
            checks = {
                "tool_called": bool(tool_calls),
                "valid_json": is_valid_json(args_raw),
                "schema_valid": bool(parsed) and validate_schema(parsed, COMPLEX_TOOL_SCHEMA),
                "required_fields_present": bool(parsed)
                and {"channel", "priority", "target", "tags"}.issubset(parsed.keys()),
            }
            if parsed:
                notes.append(f"parsed={json.dumps(parsed, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D6", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d7(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._chat(
                model,
                [
                    {"role": "user", "content": "我叫张三，请记住。"},
                    {"role": "assistant", "content": "好的，我记住了。"},
                    {"role": "user", "content": "今天天气怎么样不重要，随便回答一句。"},
                    {"role": "assistant", "content": "今天天气不错。"},
                    {"role": "user", "content": "我叫什么？只回答名字。"},
                ],
            )
            choice = response.choices[0]
            content = extract_text_from_openai_message(choice.message)
            checks = {
                "content_non_empty": bool(content),
                "contains_name": "张三" in content,
            }
            if content:
                notes.append(f"answer={content[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D7", compute_status(checks, error), "openai", now_ms() - start, checks, error, notes)

    def run_d8(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "一个水池有两个进水管和一个出水管，进水管A每小时注入3吨水，进水管B每小时注入2吨水，出水管每小时排出1吨水。水池容量为20吨，从空池开始，多久能注满？请一步步推理。"}],
            "max_tokens": self.max_tokens,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "").strip()
            reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
            if isinstance(reasoning, str):
                reasoning = reasoning.strip()
            checks = {
                "content_non_empty": bool(content),
                "reasoning_present": bool(reasoning),
            }
            if reasoning:
                notes.append(f"reasoning={str(reasoning)[:120]}")
            if content:
                notes.append(f"content={content[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        status = compute_status(checks, error)
        if status == Status.PARTIAL and checks.get("content_non_empty") and not checks.get("reasoning_present"):
            status = Status.UNSUPPORTED
            notes.append("model does not return reasoning_content field")
        return DimensionResult("D8", status, "openai", now_ms() - start, checks, error, notes)

    def run_d9(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "一个水池有两个进水管和一个出水管，进水管A每小时注入3吨水，进水管B每小时注入2吨水，出水管每小时排出1吨水。水池容量为20吨，从空池开始，多久能注满？请一步步推理。"}],
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        reasoning_parts: list[str] = []
        text_parts: list[str] = []
        saw_reasoning_delta = False
        saw_content_delta = False
        finish_reason: str | None = None
        chunk_count = 0
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines():
                        if not raw_line or not raw_line.startswith("data"):
                            continue
                        data = raw_line[len("data:"):].lstrip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        chunk_count += 1
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                        if isinstance(reasoning, str) and reasoning:
                            saw_reasoning_delta = True
                            reasoning_parts.append(reasoning)
                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            saw_content_delta = True
                            text_parts.append(content)
                        finish_reason = choices[0].get("finish_reason") or finish_reason
            full_reasoning = "".join(reasoning_parts).strip()
            full_text = "".join(text_parts).strip()
            checks = {
                "chunk_received": chunk_count > 0,
                "reasoning_delta_present": saw_reasoning_delta,
                "content_delta_present": saw_content_delta,
                "reasoning_reconstructed": bool(full_reasoning),
                "content_reconstructed": bool(full_text),
            }
            if full_reasoning:
                notes.append(f"reasoning={full_reasoning[:120]}")
            if full_text:
                notes.append(f"content={full_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        status = compute_status(checks, error)
        if status == Status.PARTIAL and checks.get("content_delta_present") and not checks.get("reasoning_delta_present"):
            status = Status.UNSUPPORTED
            notes.append("model does not return reasoning_content delta")
        return DimensionResult("D9", status, "openai", now_ms() - start, checks, error, notes)


class AnthropicRunner:
    def __init__(self, api_key: str, gateway_root: str, timeout: float, max_tokens: int) -> None:
        self.api_key = api_key
        self.gateway_root = gateway_root.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(
            api_key=api_key,
            base_url=self.gateway_root,
            timeout=timeout,
            default_headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            },
        )

    def _messages(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = self.max_tokens
        return self.client.messages.create(
            model=model,
            messages=messages,
            **kwargs,
        )

    def run_d1(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._messages(model, [{"role": "user", "content": "请只回复 OK，不要加解释。"}])
            text = flatten_anthropic_text(response.content)
            checks = {
                "role_assistant": getattr(response, "role", None) == "assistant",
                "content_non_empty": bool(text),
                "stop_reason_end_turn": getattr(response, "stop_reason", None) == "end_turn",
            }
            if text:
                notes.append(f"content={text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D1", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d2(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        url = f"{self.gateway_root}/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "请用一句中文短句介绍今天的天气。"}],
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        text_parts: list[str] = []
        chunk_count = 0
        saw_text_delta = False
        saw_message_stop = False
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines():
                        if not raw_line or not raw_line.startswith("data"):
                            continue
                        data = raw_line[len("data:"):].lstrip()
                        if data == "[DONE]":
                            break
                        event = json.loads(data)
                        chunk_count += 1
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            text = delta.get("text")
                            if isinstance(text, str):
                                saw_text_delta = True
                                text_parts.append(text)
                        if event.get("type") == "message_stop":
                            saw_message_stop = True
            full_text = "".join(text_parts).strip()
            checks = {
                "chunk_received": chunk_count > 0,
                "delta_present": saw_text_delta,
                "finish_reason_present": saw_message_stop,
                "content_reconstructed": bool(full_text),
            }
            if full_text:
                notes.append(f"stream_text={full_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D2", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d3(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._messages(
                model,
                [{"role": "user", "content": "你必须调用 get_weather 工具查询北京天气，不要直接回答。"}],
                tools=[anthropic_tool_from_openai(WEATHER_TOOL_OAI)],
            )
            tool_uses = first_anthropic_tool_uses(response.content)
            tool_use = tool_uses[0] if tool_uses else None
            tool_name = getattr(tool_use, "name", None) if tool_use else None
            tool_input = getattr(tool_use, "input", None) if tool_use else None
            checks = {
                "tool_calls_present": bool(tool_uses),
                "tool_name_match": tool_name == "get_weather",
                "arguments_valid_json": isinstance(tool_input, dict),
                "finish_reason_tool_use": getattr(response, "stop_reason", None) == "tool_use",
            }
            if tool_input:
                notes.append(f"args={json.dumps(tool_input, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D3", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d4(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._messages(
                model,
                [{"role": "user", "content": "请同时调用 get_weather 和 get_time 查询北京天气和现在几点，不要直接回答。"}],
                tools=[anthropic_tool_from_openai(WEATHER_TOOL_OAI), anthropic_tool_from_openai(TIME_TOOL_OAI)],
            )
            tool_uses = first_anthropic_tool_uses(response.content)
            tool_ids = [getattr(item, "id", None) for item in tool_uses]
            tool_names = [getattr(item, "name", None) for item in tool_uses]
            valid_inputs = all(isinstance(getattr(item, "input", None), dict) for item in tool_uses)
            checks = {
                "at_least_two_tools": len(tool_uses) >= 2,
                "distinct_tool_ids": len(set(tool_ids)) == len(tool_ids) and all(tool_ids),
                "expected_tool_names": {"get_weather", "get_time"}.issubset(set(tool_names)),
                "all_arguments_valid_json": valid_inputs,
            }
            if tool_names:
                notes.append(f"tool_names={','.join(str(name) for name in tool_names)}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D4", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d5(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            first = self._messages(
                model,
                [{"role": "user", "content": "请调用 get_weather 查询北京天气，拿到结果后再给我一句总结。"}],
                tools=[anthropic_tool_from_openai(WEATHER_TOOL_OAI)],
            )
            tool_uses = first_anthropic_tool_uses(first.content)
            if not tool_uses:
                checks = {
                    "first_turn_tool_call": False,
                    "second_turn_text": False,
                    "references_tool_result": False,
                }
            else:
                tool_use = tool_uses[0]
                second = self._messages(
                    model,
                    [
                        {"role": "user", "content": "请调用 get_weather 查询北京天气，拿到结果后再给我一句总结。"},
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": tool_use.id,
                                    "name": tool_use.name,
                                    "input": tool_use.input,
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": "北京天气晴，22C，东北风2级。",
                                }
                            ],
                        },
                    ],
                    tools=[anthropic_tool_from_openai(WEATHER_TOOL_OAI)],
                )
                second_text = flatten_anthropic_text(second.content)
                second_tool_uses = first_anthropic_tool_uses(second.content)
                checks = {
                    "first_turn_tool_call": True,
                    "second_turn_text": bool(second_text) and not second_tool_uses,
                    "references_tool_result": any(token in second_text for token in ["22", "晴", "东北风"]),
                }
                if second_text:
                    notes.append(f"roundtrip_text={second_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D5", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d6(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._messages(
                model,
                [
                    {
                        "role": "user",
                        "content": (
                            "请调用 create_alert，参数要求：channel=email，priority=high，"
                            "team=platform，region=cn，tags 至少包含 gateway 和 urgent。不要直接回答。"
                        ),
                    }
                ],
                tools=[anthropic_tool_from_openai(COMPLEX_TOOL_OAI)],
            )
            tool_uses = first_anthropic_tool_uses(response.content)
            tool_input = getattr(tool_uses[0], "input", None) if tool_uses else None
            checks = {
                "tool_called": bool(tool_uses),
                "valid_json": isinstance(tool_input, dict),
                "schema_valid": isinstance(tool_input, dict) and validate_schema(tool_input, COMPLEX_TOOL_SCHEMA),
                "required_fields_present": isinstance(tool_input, dict)
                and {"channel", "priority", "target", "tags"}.issubset(tool_input.keys()),
            }
            if isinstance(tool_input, dict):
                notes.append(f"parsed={json.dumps(tool_input, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D6", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d7(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            response = self._messages(
                model,
                [
                    {"role": "user", "content": "我叫张三，请记住。"},
                    {"role": "assistant", "content": "好的，我记住了。"},
                    {"role": "user", "content": "今天天气怎么样不重要，随便回答一句。"},
                    {"role": "assistant", "content": "今天天气不错。"},
                    {"role": "user", "content": "我叫什么？只回答名字。"},
                ],
            )
            text = flatten_anthropic_text(response.content)
            checks = {
                "content_non_empty": bool(text),
                "contains_name": "张三" in text,
            }
            if text:
                notes.append(f"answer={text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D7", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def _thinking_params(self, model: str) -> dict[str, Any]:
        # claude-4.7+ uses adaptive thinking; older models use enabled + budget_tokens
        if "4.7" in model:
            return {"thinking": {"type": "adaptive"}, "temperature": 1}
        budget = max(1024, self.max_tokens)
        max_tok = budget + self.max_tokens
        return {"thinking": {"type": "enabled", "budget_tokens": budget}, "max_tokens": max_tok, "temperature": 1}

    def run_d8(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        try:
            thinking_kwargs = self._thinking_params(model)
            response = self._messages(
                model,
                [{"role": "user", "content": "一个水池有两个进水管和一个出水管，进水管A每小时注入3吨水，进水管B每小时注入2吨水，出水管每小时排出1吨水。水池容量为20吨，从空池开始，多久能注满？请一步步推理。"}],
                **thinking_kwargs,
            )
            text = flatten_anthropic_text(response.content)
            thinking_blocks = [b for b in response.content if getattr(b, "type", None) == "thinking"]
            thinking_text = "".join(getattr(b, "thinking", "") or "" for b in thinking_blocks).strip()
            checks = {
                "content_non_empty": bool(text),
                "thinking_present": bool(thinking_text),
            }
            if thinking_text:
                notes.append(f"thinking={thinking_text[:120]}")
            if text:
                notes.append(f"content={text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D8", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)

    def run_d9(self, model: str) -> DimensionResult:
        start = now_ms()
        checks: dict[str, bool] = {}
        error: str | None = None
        notes: list[str] = []
        url = f"{self.gateway_root}/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "一个水池有两个进水管和一个出水管，进水管A每小时注入3吨水，进水管B每小时注入2吨水，出水管每小时排出1吨水。水池容量为20吨，从空池开始，多久能注满？请一步步推理。"}],
            "stream": True,
            "temperature": 1,
        }
        if "4.7" in model:
            payload["thinking"] = {"type": "adaptive"}
            payload["max_tokens"] = self.max_tokens
        else:
            budget = max(1024, self.max_tokens)
            payload["thinking"] = {"type": "enabled", "budget_tokens": budget}
            payload["max_tokens"] = budget + self.max_tokens
        thinking_parts: list[str] = []
        text_parts: list[str] = []
        saw_thinking_delta = False
        saw_text_delta = False
        saw_message_stop = False
        chunk_count = 0
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines():
                        if not raw_line or not raw_line.startswith("data"):
                            continue
                        data = raw_line[len("data:"):].lstrip()
                        if data == "[DONE]":
                            break
                        event = json.loads(data)
                        chunk_count += 1
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "thinking_delta":
                                thinking = delta.get("thinking", "")
                                if thinking:
                                    saw_thinking_delta = True
                                    thinking_parts.append(thinking)
                            elif delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    saw_text_delta = True
                                    text_parts.append(text)
                        if event.get("type") == "message_stop":
                            saw_message_stop = True
            full_thinking = "".join(thinking_parts).strip()
            full_text = "".join(text_parts).strip()
            checks = {
                "chunk_received": chunk_count > 0,
                "thinking_delta_present": saw_thinking_delta,
                "text_delta_present": saw_text_delta,
                "thinking_reconstructed": bool(full_thinking),
                "content_reconstructed": bool(full_text),
            }
            if full_thinking:
                notes.append(f"thinking={full_thinking[:120]}")
            if full_text:
                notes.append(f"content={full_text[:80]}")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return DimensionResult("D9", compute_status(checks, error), "anthropic", now_ms() - start, checks, error, notes)


def is_valid_json(raw: str) -> bool:
    if not raw:
        return False
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False


def validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> bool:
    try:
        jsonschema.validate(payload, schema)
        return True
    except jsonschema.ValidationError:
        return False


def render_status(status: Status) -> str:
    return {
        Status.PASS: "PASS",
        Status.PASS_FALLBACK: "PASS(fallback)",
        Status.PASS_SSE_COMPAT: "PASS(sse-compat)",
        Status.PARTIAL: "PARTIAL",
        Status.FAIL: "FAIL",
        Status.UNSUPPORTED: "UNSUPPORTED",
    }[status]


def run_dimension(
    dimension: str,
    model: str,
    spec: ModelSpec,
    openai_runner: OpenAICompatRunner,
    anthropic_runner: AnthropicRunner,
    force_path: str = "openai",
) -> DimensionResult:
    if force_path == "anthropic":
        return getattr(anthropic_runner, f"run_{dimension.lower()}")(model)
    openai_result = getattr(openai_runner, f"run_{dimension.lower()}")(model)
    if dimension == "D2" and openai_result.status == Status.FAIL:
        lenient_result = openai_runner.run_d2(model, lenient_sse=True)
        if lenient_result.status == Status.PASS:
            openai_result.notes.append("lenient SSE parse: PASS — gateway returns 'data:' without trailing space (non-standard)")
            openai_result.notes.append(f"lenient_stream_text={lenient_result.notes[0] if lenient_result.notes else ''}")
        return openai_result
    if openai_result.status == Status.FAIL and spec.supports_fallback:
        fallback_result = getattr(anthropic_runner, f"run_{dimension.lower()}")(model)
        if fallback_result.status == Status.PASS:
            fallback_result.status = Status.PASS_FALLBACK
        return fallback_result
    return openai_result


def print_dimension_result(model: str, result: DimensionResult) -> None:
    checks_text = ", ".join(f"{name}={'Y' if ok else 'N'}" for name, ok in result.checks.items()) or "-"
    notes_text = " | ".join(result.notes) if result.notes else "-"
    error_text = result.error or "-"
    print(
        f"{model:<24} {result.dimension:<2} {render_status(result.status):<14} "
        f"path={result.path:<10} latency={result.latency_ms:>5}ms"
    )
    print(f"  checks: {checks_text}")
    print(f"  notes : {notes_text}")
    if result.error:
        print(f"  error : {error_text}")


def print_matrix(results: dict[str, list[DimensionResult]], dims: list[str]) -> None:
    print("\nCompatibility Matrix")
    header = ["model".ljust(24)] + [dim.center(14) for dim in dims]
    print(" | ".join(header))
    print("-" * (len(" | ".join(header)) + 4))
    for model, model_results in results.items():
        result_by_dim = {item.dimension: item for item in model_results}
        row = [model.ljust(24)]
        for dim in dims:
            label = render_status(result_by_dim[dim].status)
            row.append(label.center(14))
        print(" | ".join(row))


def serialize_results(results: dict[str, list[DimensionResult]]) -> dict[str, Any]:
    return {
        model: [
            {
                "dimension": item.dimension,
                "status": item.status.value,
                "path": item.path,
                "latency_ms": item.latency_ms,
                "checks": item.checks,
                "error": item.error,
                "notes": item.notes,
            }
            for item in items
        ]
        for model, items in results.items()
    }


def validate_inputs(models: list[str], dims: list[str]) -> None:
    unknown_models = [model for model in models if model not in MODEL_SPECS]
    unknown_dims = [dim for dim in dims if dim not in DEFAULT_DIMS]
    if unknown_models:
        raise SystemExit(f"Unknown models: {', '.join(unknown_models)}")
    if unknown_dims:
        raise SystemExit(f"Unknown dims: {', '.join(unknown_dims)}")


def main() -> int:
    args = parse_args()
    models = parse_csv_args(args.model, DEFAULT_MODELS)
    dims = parse_csv_args(args.dim, DEFAULT_DIMS)
    validate_inputs(models, dims)

    api_key, api_base = load_environment()
    gateway_root = derive_gateway_root(api_base)

    openai_runner = OpenAICompatRunner(api_key, api_base, args.timeout, args.max_tokens)
    anthropic_runner = AnthropicRunner(api_key, gateway_root, args.timeout, args.max_tokens)

    print(f"OPENAI_API_BASE={api_base}")
    print(f"ANTHROPIC_GATEWAY_ROOT={gateway_root}")
    print(f"models={','.join(models)}")
    print(f"dims={','.join(dims)}")
    print(f"path={args.path}\n")

    all_results: dict[str, list[DimensionResult]] = {}
    for model in models:
        spec = MODEL_SPECS[model]
        model_results: list[DimensionResult] = []
        for dim in dims:
            result = run_dimension(dim, model, spec, openai_runner, anthropic_runner, force_path=args.path)
            model_results.append(result)
            print_dimension_result(model, result)
        all_results[model] = model_results
        print()

    print_matrix(all_results, dims)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.write_text(
            json.dumps(serialize_results(all_results), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON results written to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
