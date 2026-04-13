"""测试 rd-gateway Anthropic 原生路径是否支持 extended thinking"""

import os
import sys

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = "http://rd-gateway.patsnap.info"
MODEL = os.getenv("PLANNING_MODEL", "claude-4.6-opus")


def test_anthropic_native_thinking():
    """通过 Anthropic SDK 调用 /v1/messages，测试 thinking 是否透传"""
    import anthropic

    client = anthropic.Anthropic(
        api_key=API_KEY,
        base_url=BASE_URL,
        default_headers={
            "Authorization": f"Bearer {API_KEY}",
            "x-api-key": API_KEY,
        },
    )

    print(f"[TEST] Anthropic 原生路径 | model={MODEL} base_url={BASE_URL}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=5000,
        thinking={
            "type": "enabled",
            "budget_tokens": 2000,
        },
        messages=[
            {"role": "user", "content": "1+1等于几？请先思考再回答。"}
        ],
    )

    print(f"\n[RESULT] stop_reason={response.stop_reason}")
    print(f"[RESULT] content blocks: {len(response.content)}")

    has_thinking = False
    for block in response.content:
        print(f"  - type={block.type}")
        if block.type == "thinking":
            has_thinking = True
            print(f"    thinking preview: {block.thinking[:200]}")
        elif block.type == "text":
            print(f"    text: {block.text}")

    if has_thinking:
        print("\n✅ rd-gateway 支持 extended thinking，可以透传 thinking 内容")
    else:
        print("\n❌ rd-gateway 未返回 thinking 内容")

    return has_thinking


def test_openai_compat_thinking():
    """通过 OpenAI 兼容路径测试（对比用）"""
    import httpx
    import json

    print(f"\n[TEST] OpenAI 兼容路径 | model={MODEL}")

    payload = {
        "model": MODEL,
        "max_tokens": 500,
        "messages": [
            {"role": "user", "content": "1+1等于几？"}
        ],
    }

    resp = httpx.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    choices = data.get("choices", [])
    if choices:
        msg = choices[0].get("message", {})
        print(f"  content: {msg.get('content', '')[:200]}")
        # 检查是否有 thinking 字段
        if "thinking" in msg or "reasoning_content" in msg:
            print("  ✅ OpenAI 兼容路径也返回了 thinking 字段")
        else:
            print("  ❌ OpenAI 兼容路径无 thinking 字段")


def test_prompt_guided_thinking():
    """测试 prompt 引导的 thinking 方式"""
    import httpx
    import re

    print(f"\n[TEST] Prompt 引导 thinking | model={MODEL}")

    system_prompt = """在执行任何操作之前，先把思考过程写在 <thinking> 标签内：

格式要求：
<thinking>
[你的思考过程写在这里]
</thinking>

[然后是实际回复]"""

    payload = {
        "model": MODEL,
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": "苏州今天天气怎么样？我应该带伞吗？"}
        ],
        "system": system_prompt,
    }

    resp = httpx.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    print(f"\n完整响应:\n{content[:500]}")

    thinking_matches = re.findall(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
    if thinking_matches:
        print(f"\n✅ 找到 thinking 内容 ({len(thinking_matches)} 块):")
        for i, t in enumerate(thinking_matches):
            print(f"  [{i+1}] {t.strip()[:200]}")
        clean_answer = re.sub(r'<thinking>.*?</thinking>\s*', '', content, flags=re.DOTALL).strip()
        print(f"\n清理后的回答:\n{clean_answer[:300]}")
    else:
        print("\n❌ 未找到 <thinking> 标签，模型没有按格式输出")


if __name__ == "__main__":
    print("=" * 60)
    print("rd-gateway Extended Thinking 测试")
    print("=" * 60)

    try:
        test_openai_compat_thinking()
    except Exception as e:
        print(f"OpenAI 兼容路径测试失败: {e}")

    print()

    try:
        test_prompt_guided_thinking()
    except Exception as e:
        print(f"Prompt 引导 thinking 测试失败: {e}")

    try:
        test_anthropic_native_thinking()
    except Exception as e:
        print(f"Anthropic 原生路径测试失败: {e}")
        import traceback
        traceback.print_exc()
