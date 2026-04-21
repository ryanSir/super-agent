# RD-Gateway 多模型兼容性扩展报告

测试时间：2026-04-20  
网关地址：`http://rd-gateway.patsnap.info/v1`  
默认测试路径：OpenAI 兼容 `/v1/chat/completions`  
Claude fallback：仅在主测试维度失败时切 Anthropic 原生；本轮修正后未触发 fallback

## 先说结论

- 主测试 `D1-D7` 上，`7/9` 个模型全通过：gpt-5.4、gpt-4o、claude-4.6-opus、claude-4.6-sonnet、deepseek-r1、qwen3.5-plus、kimi-k2.5
- 仍有兼容性瑕疵的模型：gemini-3.1-pro-preview、gemini-2.5-flash
- `D2` 在上一版报告里被误判为失败；已定位为脚本 SSE 解析 bug，不是网关本身失败。
- 根因：网关返回的是合法 SSE 行 `data:{...}`，而旧脚本只接受 `data: {...}`，遗漏了“冒号后无空格”的情况。
- 修正后，9 个模型的基础流式输出都已通过。
- 真正剩余的问题集中在 Gemini 系的 OpenAI tool-calling 语义不完全兼容。
- Thinking/Reasoning 透出能力有明显分层：DeepSeek 和 Qwen 能透出实际内容；Kimi/GPT/Claude/Gemini-Flash 主要只有占位字段或不透出内容；Gemini Pro 当前只看到 metadata。

## 能力矩阵

| 模型 | 非流式输出 | 流式输出 | Thinking 非流式 | Thinking 流式 | D3 单工具 | D4 并行工具 | D5 闭环 | D6 复杂 Schema | D7 上下文 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.4 | PASS | PASS | ABSENT | PLACEHOLDER | PASS | PASS | PASS | PASS | PASS |
| gpt-4o | PASS | PASS | ABSENT | PLACEHOLDER | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-opus | PASS | PASS | ABSENT | PLACEHOLDER | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-sonnet | PASS | PASS | ABSENT | PLACEHOLDER | PASS | PASS | PASS | PASS | PASS |
| deepseek-r1 | PASS | PASS | CONTENT | CONTENT | PASS | PASS | PASS | PASS | PASS |
| gemini-3.1-pro-preview | PASS | PASS | ERROR | META_ONLY | PARTIAL | PARTIAL | PARTIAL | PASS | PASS |
| gemini-2.5-flash | PASS | PASS | ABSENT | PLACEHOLDER | PARTIAL | PARTIAL | PARTIAL | PASS | PASS |
| qwen3.5-plus | PASS | PASS | CONTENT | CONTENT | PASS | PASS | PASS | PASS | PASS |
| kimi-k2.5 | PASS | PASS | PLACEHOLDER | PLACEHOLDER | PASS | PASS | PASS | PASS | PASS |

Thinking 状态说明：

- `CONTENT`：实际透出了 reasoning/thinking 文本。
- `META_ONLY`：只看到 reasoning token 等元数据，没有思考文本。
- `PLACEHOLDER`：只看到 `reasoning_content=null`、空字符串等占位字段。
- `ABSENT`：响应里没有 reasoning/thinking 字段。
- `ERROR`：请求失败或超时。

## 严格兼容矩阵（D1-D7）

| 模型 | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.4 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| gpt-4o | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-opus | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-sonnet | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| deepseek-r1 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| gemini-3.1-pro-preview | PASS | PASS | PARTIAL | PARTIAL | PARTIAL | PASS | PASS |
| gemini-2.5-flash | PASS | PASS | PARTIAL | PARTIAL | PARTIAL | PASS | PASS |
| qwen3.5-plus | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| kimi-k2.5 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

## 排查结论

### 1. 旧版 D2 误判的根因

- 网关实际返回 `text/event-stream`。
- 原始流式数据形态是 `data:{...}`，而不是旧脚本假设的 `data: {...}`。
- 旧脚本因此没有消费到任何 chunk，误报为 `chunk_received=N`。
- 修正解析逻辑后，所有模型 `D2` 均恢复为 `PASS`。

### 2. 当前仍存在的真实兼容问题

- `gemini-2.5-flash` 与 `gemini-3.1-pro-preview` 的 `D3/D4/D5` 仍是 `PARTIAL`。
- 共同模式：单工具能触发但 `finish_reason != tool_calls`；并行工具能返回两个工具名但 `tool_call.id` 不稳定；tool result 回传后不能稳定产出最终自然语言总结。
- 这更像 OpenAI tool-calling 语义兼容不完全，而不是网关完全不可用。

### 3. Thinking 支持的实际分层

- `deepseek-r1`：非流式和流式都能透出真实 `reasoning_content`。
- `qwen3.5-plus`：非流式和流式都能透出真实 `reasoning_content`。
- `gemini-3.1-pro-preview`：流式只能看到 `reasoning_tokens` 等 metadata；非流式本轮命中过 `429`。
- `gpt-5.4`、`gpt-4o`、`claude-4.6-opus`、`claude-4.6-sonnet`、`gemini-2.5-flash`：流式里只看到 `reasoning_content=null` 占位，不透出实际思考文本。
- `kimi-k2.5`：非流式返回空字符串 `reasoning_content=""`，流式返回 `null`，也属于占位级支持。

## gpt-5.4

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 1355ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 1933ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今天天气晴朗，适合出行。 |
| D3 | 单工具调用 | PASS | openai | 1212ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city":"北京"} |
| D4 | 多工具并行调用 | PASS | openai | 1840ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 5307ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=北京当前天气：晴，22°C，东北风2级。  总结：北京今天天气晴朗，体感较舒适，适合出行。 |
| D6 | 复杂参数 Schema | PASS | openai | 2024ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 1459ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ABSENT | 928ms | 200 | - | - |
| 流式 | PLACEHOLDER | 1041ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |

## gpt-4o

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 1387ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 1891ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今天晴朗温暖，适合出游。 |
| D3 | 单工具调用 | PASS | openai | 1255ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city":"北京"} |
| D4 | 多工具并行调用 | PASS | openai | 1677ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 5270ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=北京现在天气晴朗，温度为22°C，微风轻拂，东北风2级，适合户外活动！ |
| D6 | 复杂参数 Schema | PASS | openai | 1907ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 1650ms | content_non_empty=Y, contains_name=Y | answer=张三。 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ABSENT | 915ms | 200 | - | - |
| 流式 | PLACEHOLDER | 731ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |

## claude-4.6-opus

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 2778ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 2653ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=我无法获取实时天气信息，建议您查看当地的天气预报了解今天的天气情况。 |
| D3 | 单工具调用 | PASS | openai | 2845ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city":"北京"} |
| D4 | 多工具并行调用 | PASS | openai | 2852ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 9728ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=**总结：** 北京今天天气晴朗，气温 **22°C**，吹着轻柔的 **东北风2级**，体感非常舒适，是个适合外出活动的好天气！☀️ |
| D6 | 复杂参数 Schema | PASS | openai | 2890ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 1923ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ABSENT | 2050ms | 200 | - | - |
| 流式 | PLACEHOLDER | 2083ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |

## claude-4.6-sonnet

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 2095ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 4851ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今天天气晴朗，阳光明媚，适合外出踏青。  ---  *请注意：我无法获取实时天气信息，以上为示例句子，实际天气请参考当地天气预报。* 🌤️ |
| D3 | 单工具调用 | PASS | openai | 2893ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city":"北京"} |
| D4 | 多工具并行调用 | PASS | openai | 3191ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 11258ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=以下是北京当前天气的总结：  ☀️ **北京天气晴朗**，气温舒适，当前为 **22°C**，伴有 **东北风 2 级**，风力较弱，整体来说是非常适合户外活动 |
| D6 | 复杂参数 Schema | PASS | openai | 3596ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 2238ms | content_non_empty=Y, contains_name=Y | answer=张三。 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ABSENT | 1426ms | 200 | - | - |
| 流式 | PLACEHOLDER | 1674ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |

## deepseek-r1

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 7940ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 8712ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=<think>嗯，用户让我用一句中文短句介绍今天的天气。这个请求看起来简单直接，但需要仔细处理。  用户可能正在出门前快速查看天气，或者只是想确认一下外面的情况 |
| D3 | 单工具调用 | PASS | openai | 3268ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city": "北京"} |
| D4 | 多工具并行调用 | PASS | openai | 4147ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 7275ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=北京的天气晴朗，气温22摄氏度，东北风2级，非常适合户外活动。 |
| D6 | 复杂参数 Schema | PASS | openai | 5798ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "target": {"team": "platform", "region": "cn"}, "tags": ["gateway", "urgent"]} |
| D7 | 多轮上下文保持 | PASS | openai | 5480ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | CONTENT | 14162ms | 200 | $.choices[0].message.reasoning_content="首先，用户要求我认真思考后回答37乘以19等于多少，并且只输出最终答案。这意味着我需要计算这个乘法，但不要显示任何思考过程。\n\n计算37乘以19。我可以使用乘法公式：37 × 19。\n\n我可以分解19为20减1，因为乘法有时更容易 / $.usage.completion_tokens_details.reasoning_tokens=476 | - |
| 流式 | CONTENT | 8382ms | 200 | $.choices[0].delta.reasoning_content="" / $.choices[0].delta.reasoning_content=" " / $.choices[0].delta.reasoning_content="首先" | - |

## gemini-3.1-pro-preview

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 2835ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 4126ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今天阳光明媚，微风不燥 |
| D3 | 单工具调用 | PARTIAL | openai | 3625ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=N | args={"city":"北京"} |
| D4 | 多工具并行调用 | PARTIAL | openai | 8565ms | at_least_two_tools=Y, distinct_tool_ids=N, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PARTIAL | openai | 12514ms | first_turn_tool_call=Y, second_turn_text=N, references_tool_result=N | - |
| D6 | 复杂参数 Schema | PASS | openai | 7863ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 5576ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ERROR | 473ms | 429 | - | Client error '429 Too Many Requests' for url 'http://rd-gateway.patsnap.info/v1/chat/completions' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429 |
| 流式 | META_ONLY | 5179ms | 200 | $.choices[0].delta.reasoning_content=null / $.usage.completion_tokens_details.reasoning_tokens=243 | - |

## gemini-2.5-flash

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 1142ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 1019ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今天天气晴朗，微风习习。 |
| D3 | 单工具调用 | PARTIAL | openai | 838ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=N | args={"city":"北京"} |
| D4 | 多工具并行调用 | PARTIAL | openai | 904ms | at_least_two_tools=Y, distinct_tool_ids=N, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PARTIAL | openai | 1700ms | first_turn_tool_call=Y, second_turn_text=N, references_tool_result=N | - |
| D6 | 复杂参数 Schema | PASS | openai | 1205ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "tags": ["gateway", "urgent"], "target": {"region": "cn", "team": "platform"}} |
| D7 | 多轮上下文保持 | PASS | openai | 852ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | ABSENT | 796ms | 200 | - | - |
| 流式 | PLACEHOLDER | 871ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |

## qwen3.5-plus

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 6452ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 77882ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=请告诉我您所在的城市，以便我为您查询今天的天气。 |
| D3 | 单工具调用 | PASS | openai | 2088ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city": "北京"} |
| D4 | 多工具并行调用 | PASS | openai | 3141ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 4316ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=北京今天天气晴朗，气温22摄氏度，东北风2级，是个适合外出的好天气。 |
| D6 | 复杂参数 Schema | PASS | openai | 5068ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "target": {"team": "platform", "region": "cn"}, "tags": ["gateway", "urgent"]} |
| D7 | 多轮上下文保持 | PASS | openai | 5605ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | CONTENT | 8445ms | 200 | $.choices[0].message.reasoning_content="Thinking Process:\n\n1.  **Analyze the Request:**\n    *   Task: Calculate 37 multiplied by 19 (37 乘以 19 等于多少).\n    * / $.usage.completion_tokens_details.reasoning_tokens=424 | - |
| 流式 | CONTENT | 12774ms | 200 | $.choices[0].delta.reasoning_content="Thinking" / $.choices[0].delta.reasoning_content=" Process:\n\n1" / $.choices[0].delta.reasoning_content=".  **An" | - |

## kimi-k2.5

| 维度 | 说明 | 结果 | 路径 | 延迟 | 检查项 | 备注/错误 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 基础文本生成 | PASS | openai | 918ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | content=OK |
| D2 | 流式输出 | PASS | openai | 2146ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | stream_text=今日晴朗，微风拂面。 |
| D3 | 单工具调用 | PASS | openai | 2866ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | args={"city": "北京"} |
| D4 | 多工具并行调用 | PASS | openai | 1495ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | tool_names=get_weather,get_time |
| D5 | 工具结果回传闭环 | PASS | openai | 3586ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | roundtrip_text=**总结**：北京今天天气晴朗，气温22℃，东北风2级，是个舒适宜人的好天气！☀️ |
| D6 | 复杂参数 Schema | PASS | openai | 2073ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | parsed={"channel": "email", "priority": "high", "target": {"team": "platform", "region": "cn"}, "tags": ["gateway", "urgent"]} |
| D7 | 多轮上下文保持 | PASS | openai | 1183ms | content_non_empty=Y, contains_name=Y | answer=张三 |

| Thinking 探测 | 结果 | 延迟 | HTTP | 证据 | 错误 |
| --- | --- | --- | --- | --- | --- |
| 非流式 | PLACEHOLDER | 2902ms | 200 | $.choices[0].message.reasoning_content="" | - |
| 流式 | PLACEHOLDER | 844ms | 200 | $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null / $.choices[0].delta.reasoning_content=null | - |
