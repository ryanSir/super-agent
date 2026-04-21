# RD-Gateway 多模型兼容性测试报告

测试时间：2026-04-20
网关地址：`http://rd-gateway.patsnap.info/v1`
测试路径：OpenAI 兼容（`/v1/chat/completions`）

---

## 兼容矩阵

| 模型 | D1 文本生成 | D2 流式输出 | D3 单工具 | D4 并行工具 | D5 工具闭环 | D6 复杂Schema | D7 多轮上下文 | D8 思考(非流式) | D9 思考(流式) |
|------|:-----------:|:-----------:|:---------:|:-----------:|:-----------:|:-------------:|:-------------:|:---------------:|:-------------:|
| gpt-5.4 | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ➖ UNSUPPORTED | ➖ UNSUPPORTED |
| gpt-4o | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ➖ UNSUPPORTED | ➖ UNSUPPORTED |
| claude-4.7-opus | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ➖ UNSUPPORTED | ➖ UNSUPPORTED |
| claude-4.6-sonnet | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ➖ UNSUPPORTED | ➖ UNSUPPORTED |
| deepseek-r1 | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| gemini-2.5-flash | ✅ PASS | ❌ FAIL | ⚠️ PARTIAL | ⚠️ PARTIAL | ⚠️ PARTIAL | ✅ PASS | ✅ PASS | ➖ UNSUPPORTED | ➖ UNSUPPORTED |
| qwen3.5-plus | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| kimi-k2.5 | ✅ PASS | ❌ 429 | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ 429 | ❌ 429 |
| doubao-seed-2.0-pro | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| glm-5 | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| minimax-2.7 | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ⚠️ PARTIAL | ⚠️ PARTIAL |

---

## 维度说明

| 维度 | 说明 | 验证目标 |
|------|------|----------|
| D1 | 基础文本生成 | 非流式请求，返回 status 200、content 非空、role=assistant、finish_reason=stop |
| D2 | 流式输出 | stream=True，SSE chunk 格式标准、delta 完整、finish_reason 正确 |
| D3 | 单工具调用 | 定义 get_weather 工具，验证 tool_calls 字段、function.name、arguments JSON 合法 |
| D4 | 多工具并行调用 | 两个工具同时调用，验证 tool_calls 数组长度 ≥2、独立 id、name 正确 |
| D5 | 工具结果回传闭环 | 触发工具调用 → 回传 tool_result → 模型基于结果生成文本回答 |
| D6 | 复杂参数 Schema | 包含 enum、嵌套 object、array、多 required 字段，验证 JSON schema 合规 |
| D7 | 多轮对话上下文 | 三轮对话，验证网关正确透传 messages 历史 |
| D8 | 思考过程(非流式) | 非流式请求，验证响应中 reasoning_content 字段是否返回 |
| D9 | 思考过程(流式) | 流式请求，验证 delta 中 reasoning_content 增量是否正常透传 |

---

## 状态说明

| 状态 | 含义 |
|------|------|
| ✅ PASS | 所有检查项通过 |
| ❌ FAIL | 请求失败或检查项不满足 |
| ⚠️ PARTIAL | 请求成功但部分检查项未通过 |
| 🔄 PASS(fallback) | OpenAI 路径失败，Anthropic 原生路径通过（仅 Claude） |
| ➖ UNSUPPORTED | 模型不支持该能力（如非推理模型无 reasoning_content） |

---

## gpt-5.4 详情（OpenAI）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 986ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 1019ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准：`data:` 后缺少空格，不符合 RFC 规范 |
| D3 单工具调用 | ✅ PASS | 1369ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 1600ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 2273ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 1363ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 1244ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ➖ UNSUPPORTED | 2788ms | content_non_empty=Y, reasoning_present=N | 模型不返回 reasoning_content 字段 |
| D9 思考(流式) | ➖ UNSUPPORTED | 3872ms | chunk_received=Y, reasoning_delta_present=N, content_delta_present=Y | 模型不返回 reasoning_content delta |

---

## gpt-4o 详情（OpenAI）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 894ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 1227ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准：`data:` 后缺少空格，不符合 RFC 规范 |
| D3 单工具调用 | ✅ PASS | 724ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 1003ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 2140ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 1028ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 1497ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ➖ UNSUPPORTED | 4592ms | content_non_empty=Y, reasoning_present=N | 模型不返回 reasoning_content 字段 |
| D9 思考(流式) | ➖ UNSUPPORTED | 5697ms | chunk_received=Y, reasoning_delta_present=N, content_delta_present=Y | 模型不返回 reasoning_content delta |

---

## claude-4.7-opus 详情（Anthropic — OpenAI 兼容路径）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 2379ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 2177ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准：`data:` 后缺少空格，不符合 RFC 规范 |
| D3 单工具调用 | ✅ PASS | 1842ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 2023ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 3586ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 2434ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 1201ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ➖ UNSUPPORTED | 3196ms | content_non_empty=Y, reasoning_present=N | OpenAI 兼容路径不返回 reasoning_content，Claude thinking 需走 Anthropic 原生路径 |
| D9 思考(流式) | ➖ UNSUPPORTED | 3278ms | chunk_received=Y, reasoning_delta_present=N, content_delta_present=Y | 同上，OpenAI 兼容路径无 reasoning delta |

---

## claude-4.6-sonnet 详情（Anthropic — OpenAI 兼容路径）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 4124ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 4157ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准：`data:` 后缺少空格，不符合 RFC 规范 |
| D3 单工具调用 | ✅ PASS | 2043ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 2842ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 5819ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 3324ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 4045ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ➖ UNSUPPORTED | 4562ms | content_non_empty=Y, reasoning_present=N | OpenAI 兼容路径不返回 reasoning_content |
| D9 思考(流式) | ➖ UNSUPPORTED | 4754ms | chunk_received=Y, reasoning_delta_present=N, content_delta_present=Y | 同上 |

---

## deepseek-r1 详情（DeepSeek）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 5414ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 6755ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准 |
| D3 单工具调用 | ✅ PASS | 2271ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 12962ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | 延迟较高，推理模型特性 |
| D5 工具回传闭环 | ✅ PASS | 11208ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 9877ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 5923ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ✅ PASS | 20791ms | content_non_empty=Y, reasoning_present=Y | reasoning_content 字段正常返回 |
| D9 思考(流式) | ✅ PASS | 27413ms | chunk_received=Y, reasoning_delta_present=Y, content_delta_present=Y, reasoning_reconstructed=Y, content_reconstructed=Y | reasoning delta 正常透传；注意 content 中混入了 `<think>` 标签，客户端需过滤 |

---

## gemini-2.5-flash 详情（Google）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 1075ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 1030ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准 |
| D3 单工具调用 | ⚠️ PARTIAL | 902ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=N | 工具调用成功但 finish_reason 不是 tool_calls |
| D4 多工具并行 | ⚠️ PARTIAL | 860ms | at_least_two_tools=Y, distinct_tool_ids=N, expected_tool_names=Y, all_arguments_valid_json=Y | tool_ids 不唯一，Agent 回传会出问题 |
| D5 工具回传闭环 | ⚠️ PARTIAL | 1598ms | first_turn_tool_call=Y, second_turn_text=N, references_tool_result=N | 第一轮工具调用成功，但回传后第二轮未返回文本回答，闭环断裂 |
| D6 复杂参数 | ✅ PASS | 958ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 700ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ➖ UNSUPPORTED | 2099ms | content_non_empty=Y, reasoning_present=N | 不返回 reasoning_content |
| D9 思考(流式) | ➖ UNSUPPORTED | 2039ms | chunk_received=Y, reasoning_delta_present=N, content_delta_present=Y | 不返回 reasoning delta |

---

## qwen3.5-plus 详情（阿里）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 4630ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 100284ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准；注意流式延迟极高（100s） |
| D3 单工具调用 | ✅ PASS | 1824ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 3101ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 12893ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 6015ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 5866ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ✅ PASS | 32636ms | content_non_empty=Y, reasoning_present=Y | reasoning_content 正常返回（英文思考过程） |
| D9 思考(流式) | ✅ PASS | 19367ms | chunk_received=Y, reasoning_delta_present=Y, content_delta_present=Y, reasoning_reconstructed=Y, content_reconstructed=Y | reasoning delta 正常透传 |

---

## kimi-k2.5 详情（Moonshot）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 989ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 1704ms | - | 429 Too Many Requests，需重测 |
| D3 单工具调用 | ✅ PASS | 3369ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 1806ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 5987ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 6235ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 4565ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ❌ FAIL | 1500ms | - | 429 Too Many Requests，需重测 |
| D9 思考(流式) | ❌ FAIL | 2281ms | - | 429 Too Many Requests，需重测 |

---

## doubao-seed-2.0-pro 详情（ByteDance）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 2285ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 25059ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准 |
| D3 单工具调用 | ✅ PASS | 4627ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 8639ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 13590ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 10469ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 3410ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ✅ PASS | 31737ms | content_non_empty=Y, reasoning_present=Y | reasoning_content 正常返回（中文思考过程） |
| D9 思考(流式) | ✅ PASS | 26981ms | chunk_received=Y, reasoning_delta_present=Y, content_delta_present=Y, reasoning_reconstructed=Y, content_reconstructed=Y | reasoning delta 正常透传 |

---

## glm-5 详情（智谱）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 3815ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 18173ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 网关 SSE 格式不标准 |
| D3 单工具调用 | ✅ PASS | 4133ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 7625ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 12743ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 6030ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 5846ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ✅ PASS | 25212ms | content_non_empty=Y, reasoning_present=Y | reasoning_content 正常返回 |
| D9 思考(流式) | ✅ PASS | 21705ms | chunk_received=Y, reasoning_delta_present=Y, content_delta_present=Y, reasoning_reconstructed=Y, content_reconstructed=Y | reasoning delta 正常透传 |

---

## minimax-2.7 详情（MiniMax）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 4241ms | has_choice=Y, role_assistant=Y, content_non_empty=Y, finish_reason_stop=Y | |
| D2 流式输出 | ❌ FAIL | 7473ms | chunk_received=N, delta_present=N, finish_reason_present=N, content_reconstructed=N | 宽松解析也未通过，可能是流式格式与标准 SSE 差异更大 |
| D3 单工具调用 | ✅ PASS | 1642ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_calls=Y | |
| D4 多工具并行 | ✅ PASS | 4172ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 9176ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 4580ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 2468ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ⚠️ PARTIAL | 7103ms | content_non_empty=N, reasoning_present=Y | reasoning 有返回但 content 为空，思考过程可能占满 max_tokens |
| D9 思考(流式) | ⚠️ PARTIAL | 9652ms | chunk_received=Y, reasoning_delta_present=Y, content_delta_present=N, reasoning_reconstructed=Y, content_reconstructed=N | 同上，reasoning delta 正常但无 content delta |

---

## 问题汇总

| # | 维度 | 模型 | 问题 | 归因 |
|---|------|------|------|------|
| 1 | D2 | gpt-5.4 | SSE 格式 `data:` 后缺少空格，不符合 RFC 规范 | 网关 |
| 2 | D2 | gpt-4o | SSE 格式 `data:` 后缺少空格，不符合 RFC 规范（同 gpt-5.4） | 网关 |
| 3 | D2 | claude-4.7-opus | SSE 格式 `data:` 后缺少空格，不符合 RFC 规范（同上） | 网关 |
| 4 | D2 | claude-4.6-sonnet | SSE 格式 `data:` 后缺少空格，不符合 RFC 规范（同上） | 网关 |
| 5 | D2 | deepseek-r1 | SSE 格式 `data:` 后缺少空格，不符合 RFC 规范（同上） | 网关 |
| 6 | D2 | gemini-2.5-flash | SSE 格式 `data:` 后缺少空格（同上） | 网关 |
| 7 | D2 | qwen3.5-plus | SSE 格式 `data:` 后缺少空格（同上）；流式延迟极高（100s） | 网关 |
| 8 | D8/D9 | claude-4.7-opus | OpenAI 兼容路径不返回 reasoning_content，Claude thinking 需走 Anthropic 原生路径 | 协议差异 |
| 9 | D8/D9 | claude-4.6-sonnet | 同上 | 协议差异 |
| 10 | D9 | deepseek-r1 | 流式 content 中混入 `<think>` 标签，客户端需做过滤 | 网关/模型 |
| 11 | D3 | gemini-2.5-flash | 工具调用成功但 finish_reason 不是 tool_calls | 网关转译 |
| 12 | D4 | gemini-2.5-flash | 并行工具调用 tool_ids 不唯一，Agent 回传会出问题 | 网关转译 |
| 13 | D5 | gemini-2.5-flash | 工具结果回传后第二轮未返回文本回答，闭环断裂 | 网关转译 |
| 14 | D2/D8/D9 | kimi-k2.5 | 429 Too Many Requests 限流，需重测 | 配额 |
| 15 | D2 | doubao-seed-2.0-pro | SSE 格式 `data:` 后缺少空格（同上） | 网关 |
| 16 | D2 | glm-5 | SSE 格式 `data:` 后缺少空格（同上） | 网关 |
| 17 | D2 | minimax-2.7 | 流式输出失败，宽松解析也未通过 | 待排查 |
| 18 | D8/D9 | minimax-2.7 | reasoning 有返回但 content 为空，思考过程可能占满 max_tokens | 模型/参数 |

---

## 结论

11 个模型测试完毕（kimi-k2.5 部分维度因 429 限流需重测）。

Agent 场景可用性分级：

- 完全可用（D1-D7 全 PASS + D8/D9 PASS）：deepseek-r1、qwen3.5-plus、doubao-seed-2.0-pro、glm-5
- 工具调用可用（D1、D3-D7 全 PASS）：gpt-5.4、gpt-4o、claude-4.7-opus、claude-4.6-sonnet、minimax-2.7
- 待重测：kimi-k2.5（D2/D8/D9 限流）
- 工具调用有缺陷：gemini-2.5-flash（finish_reason 不标准、tool_ids 重复、回传闭环断裂）

全局问题：D2 流式输出所有模型均 FAIL，根因是网关 SSE 格式 `data:` 后缺少空格，不符合 RFC 规范，需网关侧修复。
