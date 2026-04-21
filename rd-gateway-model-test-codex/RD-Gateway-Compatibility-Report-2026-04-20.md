# RD-Gateway 多模型兼容性测试报告

测试时间：2026-04-20  
测试目录：`/Users/zhangyang/Desktop/temp/super-agent/rd-gateway-model-test-codex`  
执行脚本：`gateway_compat_test.py`

## 测试策略

- 默认全部模型先走 OpenAI 兼容路径：`/v1/chat/completions`
- 仅 Claude 系列在某个维度 `FAIL` 时，自动 fallback 到 Anthropic 原生：`/v1/messages`
- 测试维度：
  - `D1` 基础文本生成
  - `D2` 流式输出
  - `D3` 单工具调用
  - `D4` 多工具并行调用
  - `D5` 工具结果回传闭环
  - `D6` 复杂参数 Schema
  - `D7` 多轮上下文保持

状态定义：

- `PASS`：当前路径通过
- `PASS(fallback)`：OpenAI 失败，Claude fallback 到 Anthropic 原生后通过
- `PARTIAL`：请求成功，但检查项不完全满足
- `FAIL`：请求失败，或检查项完全不满足

## 执行结论

这轮结果很集中，说明问题主要不在“基础调用”而在“协议细节和个别模型兼容性”：

- `D2 Streaming` 是系统性失败项。9 个模型全部未通过，其中 Claude fallback 到 Anthropic 原生后仍失败。
- OpenAI 系、Kimi、Qwen、Claude 在 `D1/D3/D4/D5/D6/D7` 上整体可用，说明文本、多轮上下文、工具调用主链路基本可跑。
- `deepseek-r1` 的主要问题在 `D4`，没有稳定返回 2 个并行工具调用。
- `gemini-2.5-flash` 在工具调用相关维度存在协议不完全兼容，特别是 `finish_reason`、并行调用的 `id`、以及 tool result 回传闭环。
- `gemini-3.1-pro-preview` 本轮基本不可评估，绝大多数失败来自 `429 RESOURCE_EXHAUSTED`，更像额度或限流问题，不是纯协议结论。
- 本轮没有出现任何 `PASS(fallback)`，说明 Claude 的 fallback 路径并没有补上 OpenAI 路径的失败项；至少在当前网关实现下，Anthropic 原生流式也同样不可用。

## 兼容矩阵

| 模型 | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.4 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |
| gpt-4o | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-opus | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |
| claude-4.6-sonnet | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |
| deepseek-r1 | PASS | FAIL | PASS | PARTIAL | PASS | PASS | PASS |
| gemini-3.1-pro-preview | FAIL | FAIL | FAIL | PARTIAL | FAIL | FAIL | FAIL |
| gemini-2.5-flash | PASS | FAIL | PARTIAL | PARTIAL | PARTIAL | PASS | PASS |
| qwen3.5-plus | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |
| kimi-k2.5 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS |

## 关键发现

### 1. Streaming 是网关级问题，不是单模型问题

所有模型 `D2` 都失败，且失败模式高度一致：

- `chunk_received = N`
- `delta_present = N`
- `finish_reason_present = N`
- `content_reconstructed = N`

这说明当前 `rd-gateway` 在流式链路上至少存在以下一种问题：

- 没有真正返回标准 SSE chunk
- 返回了 chunk，但格式不符合 OpenAI / Anthropic 客户端预期
- 中间层把流式响应缓冲成了非流式返回

Claude fallback 到 Anthropic 原生后，`D2` 仍然失败，说明这不是单纯的 OpenAI 兼容层转译问题，更像是网关整体流式输出链路异常。

### 2. Agent 工具调用主链路整体可用

以下模型在 `D3-D6` 上表现稳定：

- `gpt-5.4`
- `gpt-4o`
- `claude-4.6-opus`
- `claude-4.6-sonnet`
- `qwen3.5-plus`
- `kimi-k2.5`

这意味着在当前网关下，这几类模型已经基本具备 Agent 场景的核心能力：

- 单工具调用
- 多工具并行调用
- 工具结果回传闭环
- 复杂参数 schema

### 3. 部分模型存在业务层兼容性缺口

`deepseek-r1`：

- `D4 = PARTIAL`
- 只保证了 `arguments` 是合法 JSON
- 没有稳定返回 2 个工具调用，也没有满足预期工具名和独立 id

结论：可用于单工具 Agent，但并行工具调用不稳定。

`gemini-2.5-flash`：

- `D3 = PARTIAL`：有 tool call，但 `finish_reason != tool_calls`
- `D4 = PARTIAL`：能返回两个工具名，但 `tool id` 不稳定
- `D5 = PARTIAL`：首轮会调工具，但 tool result 回传后不能稳定转成自然语言总结

结论：表面支持工具调用，但协议细节不完全符合预期，不适合直接用于严格依赖 OpenAI tool-calling 语义的 Agent 框架。

### 4. Gemini 3.1 Pro Preview 当前结果不能直接当作协议结论

`gemini-3.1-pro-preview` 的大部分失败是：

- `429 Too Many Requests`
- `RESOURCE_EXHAUSTED`

因此本轮更准确的判断是：

- 当前网关或上游配额状态下不可稳定测试
- 不能仅凭这轮结果断言其 OpenAI 兼容能力一定不行

但它在唯一成功返回的 `D4` 中也只是 `PARTIAL`，因此至少不能视为“已验证可用于 Agent”。

## 逐模型摘要

### gpt-5.4

- `6 PASS / 1 FAIL`
- 仅 `D2` 失败
- 最慢维度：`D5`，2126ms
- 结论：除流式外，OpenAI 兼容层可直接用于 Agent

### gpt-4o

- `6 PASS / 1 FAIL`
- 仅 `D2` 失败
- 最慢维度：`D5`，3042ms
- 结论：除流式外，OpenAI 兼容层可直接用于 Agent

### claude-4.6-opus

- `6 PASS / 1 FAIL`
- `D2` 在 OpenAI 失败后 fallback 到 Anthropic 原生仍失败
- 最慢维度：`D5`，5658ms
- 结论：除流式外，OpenAI 兼容层已可用；fallback 没有带来额外收益

### claude-4.6-sonnet

- `6 PASS / 1 FAIL`
- `D2` 在 OpenAI 失败后 fallback 到 Anthropic 原生仍失败
- 最慢维度：`D5`，5776ms
- 结论：除流式外，OpenAI 兼容层已可用；fallback 没有带来额外收益

### deepseek-r1

- `5 PASS / 1 PARTIAL / 1 FAIL`
- `D2` 失败，`D4` 并行工具调用不稳定
- 最慢维度：`D7`，12715ms
- 结论：适合简单 Agent，不适合依赖并行工具调用的场景

### gemini-2.5-flash

- `3 PASS / 3 PARTIAL / 1 FAIL`
- 工具调用相关维度存在明显协议细节偏差
- 最慢维度：`D5`，1958ms
- 结论：当前不建议作为严格 OpenAI tool-calling Agent 的首选模型

### gemini-3.1-pro-preview

- `0 PASS / 1 PARTIAL / 6 FAIL`
- 主要失败原因是 `429 RESOURCE_EXHAUSTED`
- 最慢维度：`D2`，7010ms
- 结论：当前不可作为兼容性结论依据，需要先解除配额/限流问题再重测

### qwen3.5-plus

- `6 PASS / 1 FAIL`
- 仅 `D2` 失败
- 最慢维度：`D2`，58881ms
- 结论：除流式外，OpenAI 兼容层可直接用于 Agent；但流式失败等待时间异常长

### kimi-k2.5

- `6 PASS / 1 FAIL`
- 仅 `D2` 失败
- 最慢维度：`D5`，2888ms
- 结论：除流式外，OpenAI 兼容层可直接用于 Agent

## 建议

优先级最高的修复项：

1. 排查 `rd-gateway` 的流式响应链路，重点看 SSE `Content-Type`、chunk flush、代理层缓冲、以及 OpenAI/Anthropic 两套流式事件格式。
2. 对 `gemini-2.5-flash` 做专项协议对齐，重点看 `finish_reason`、tool call id、tool result round-trip。
3. 对 `deepseek-r1` 补一轮并行工具调用专项测试，确认是模型能力问题还是网关转译丢失多工具结构。
4. 对 `gemini-3.1-pro-preview` 在解除 `429` 之后重跑全量，当前结果不能直接作为协议不兼容结论。

如果以“当前就要选一批能用于 Agent 的模型”为目标，本轮可以暂时归为：

- 可用但不支持流式：`gpt-5.4`、`gpt-4o`、`claude-4.6-opus`、`claude-4.6-sonnet`、`qwen3.5-plus`、`kimi-k2.5`
- 有条件可用：`deepseek-r1`
- 暂不建议用于严格 Agent tool-calling：`gemini-2.5-flash`
- 暂不可评估：`gemini-3.1-pro-preview`

## 产出文件

- 原始结果 JSON：`results/*.json`
- 执行脚本：`gateway_compat_test.py`
- 本报告：`RD-Gateway-Compatibility-Report-2026-04-20.md`
