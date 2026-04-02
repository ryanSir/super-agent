import os
from openai import OpenAI

client = OpenAI(
    api_key="sk-gigusepkibdoqiovwfktlncihpvwqkwvchbrelaggxsxuzdv",
    base_url="https://api.siliconflow.cn/v1",
)
completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=[{'role': 'user', 'content': '我当前还有多少钱'}]
)
print(completion.choices[0].message.content)