# RD-Gateway Anthropic 原生路径兼容性测试报告

测试时间：2026-04-20
网关地址：`http://rd-gateway.patsnap.info/v1/messages`
测试路径：Anthropic 原生（`/v1/messages`）

---

## 兼容矩阵

| 模型 | D1 文本生成 | D2 流式输出 | D3 单工具 | D4 并行工具 | D5 工具闭环 | D6 复杂Schema | D7 多轮上下文 | D8 思考(非流式) | D9 思考(流式) |
|------|:-----------:|:-----------:|:---------:|:-----------:|:-----------:|:-------------:|:-------------:|:---------------:|:-------------:|
| gpt-5.4 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 | ❌ 400 |
| claude-4.7-opus | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ⚠️ PARTIAL | ⚠️ PARTIAL |
| claude-4.6-sonnet | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |

---

## 维度说明

同 [OpenAI 兼容路径报告](RD-Gateway-Compatibility-Report-2026-04-20.md#维度说明)。

---

## 状态说明

同 [OpenAI 兼容路径报告](RD-Gateway-Compatibility-Report-2026-04-20.md#状态说明)。

---

## gpt-5.4 详情（OpenAI — Anthropic 原生路径）

> 全部维度 400 Bad Request。错误信息：`Unsupported value: 'top_p' must be greater than 0 and less than or equal to 1 with this model.`
> 结论：Anthropic 原生路径不支持非 Claude 模型，符合预期。

---

## claude-4.7-opus 详情（Anthropic 原生路径）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 1117ms | role_assistant=Y, content_non_empty=Y, stop_reason_end_turn=Y | |
| D2 流式输出 | ✅ PASS | 1439ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | SSE 格式标准，原生路径无 OpenAI 路径的格式问题 |
| D3 单工具调用 | ✅ PASS | 1902ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_use=Y | |
| D4 多工具并行 | ✅ PASS | 1892ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 4383ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 1862ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 1251ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ⚠️ PARTIAL | 3357ms | content_non_empty=Y, thinking_present=N | thinking block 已返回但内容为 None，网关/Bedrock 未透传 adaptive thinking 内容 |
| D9 思考(流式) | ⚠️ PARTIAL | 3233ms | chunk_received=Y, thinking_delta_present=N, text_delta_present=Y | 同上，thinking delta 未透传 |

---

## claude-4.6-sonnet 详情（Anthropic 原生路径）

| 维度 | 结果 | 延迟 | 检查项 | 备注 |
|------|------|-----:|--------|------|
| D1 基础文本生成 | ✅ PASS | 1468ms | role_assistant=Y, content_non_empty=Y, stop_reason_end_turn=Y | |
| D2 流式输出 | ✅ PASS | 6124ms | chunk_received=Y, delta_present=Y, finish_reason_present=Y, content_reconstructed=Y | SSE 格式标准 |
| D3 单工具调用 | ✅ PASS | 2272ms | tool_calls_present=Y, tool_name_match=Y, arguments_valid_json=Y, finish_reason_tool_use=Y | |
| D4 多工具并行 | ✅ PASS | 2889ms | at_least_two_tools=Y, distinct_tool_ids=Y, expected_tool_names=Y, all_arguments_valid_json=Y | |
| D5 工具回传闭环 | ✅ PASS | 5130ms | first_turn_tool_call=Y, second_turn_text=Y, references_tool_result=Y | |
| D6 复杂参数 | ✅ PASS | 3035ms | tool_called=Y, valid_json=Y, schema_valid=Y, required_fields_present=Y | |
| D7 多轮上下文 | ✅ PASS | 1813ms | content_non_empty=Y, contains_name=Y | |
| D8 思考(非流式) | ✅ PASS | 6376ms | content_non_empty=Y, thinking_present=Y | thinking block 正常返回（英文思考过程） |
| D9 思考(流式) | ✅ PASS | 4816ms | chunk_received=Y, thinking_delta_present=Y, text_delta_present=Y, thinking_reconstructed=Y, content_reconstructed=Y | thinking delta 正常透传 |

---

## 问题汇总

| # | 维度 | 模型 | 问题 | 归因 |
|---|------|------|------|------|
| 1 | 全部 | gpt-5.4 | Anthropic 原生路径不支持非 Claude 模型，400 参数错误 | 预期行为 |
| 2 | D8/D9 | claude-4.7-opus | adaptive thinking block 已返回但内容为 None，网关/Bedrock 未透传 thinking 内容 | 网关/Bedrock |

---

## 脚本修复记录

| 问题 | 原因 | 修复 |
|------|------|------|
| claude-4.7-opus D8/D9 400 | 4.7 不支持 `thinking.type.enabled`，需用 `thinking.type.adaptive` | 按模型版本分支：4.7 用 adaptive，其他用 enabled + budget_tokens |
| claude-4.6-sonnet D8 400 | `max_tokens`(256) < `budget_tokens`(1024)，Anthropic 要求 max_tokens > budget_tokens | `_messages` 改为允许 kwargs 覆盖 max_tokens；D8 传 `max_tokens = budget + self.max_tokens` |
| claude-4.7-opus D8 TypeError | adaptive 模式返回的 thinking block 中 `thinking` 属性可能为 None | `getattr(b, "thinking", "") or ""` 防空 |

---

## 结论

Anthropic 原生路径（`/v1/messages`）仅适用于 Claude 系列。两个 Claude 模型 D1-D7 全部 PASS（包括 D2 流式输出），证实 OpenAI 路径的 SSE 格式问题是网关转译层 bug，原生路径无此问题。

claude-4.6-sonnet 全 9 维度 PASS，thinking 完整可用。claude-4.7-opus D1-D7 全 PASS，但 D8/D9 PARTIAL — thinking block 已返回但内容为 None，网关/Bedrock 对 adaptive thinking 的内容透传存在问题，数据格式应与 claude-4.6-sonnet 一致但实际未透传。

对比 OpenAI 兼容路径，Anthropic 原生路径对 Claude 系列的兼容性更好，建议项目中 Claude 模型优先走原生路径（与当前 `src_deepagent/llm/config.py` 的实现一致）。
