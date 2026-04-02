from openai import OpenAI

client = OpenAI(
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJoZWFkZXIiOiJYLUNyZWRlbnRpYWwtVXNlcm5hbWUiLCJvYmplY3QiOiJ6aGFuZ3lhbmcifQ.N5I847rwXHCbwKahLLMjUC0K2DAbZlquVFAk9bHwPmc",
    base_url="http://rd-gateway.patsnap.info/v1",
)

# 模拟 PydanticAI 的请求方式：流式 + tool_calls
stream = client.chat.completions.create(
    model="claude-4.5-sonnet",
    stream=True,
    messages=[{'role': 'user', 'content': '帮我创建一个代码优化工具'}],
    tool_choice="required",
    tools=[{
        "type": "function",
        "function": {
            "name": "create_skill",
            "description": "创建 Skill",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name", "description"],
            },
        },
    }],
)

args = ""
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.tool_calls:
        for tc in chunk.choices[0].delta.tool_calls:
            if tc.function and tc.function.arguments:
                args += tc.function.arguments

print("拼接结果:", args)
import json

try:
    json.loads(args)
    print("JSON 有效")
except json.JSONDecodeError as e:
    print(f"JSON 截断: {e}")