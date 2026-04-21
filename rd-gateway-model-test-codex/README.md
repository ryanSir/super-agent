# RD-Gateway Model Test Codex

按你确认的策略实现：

- 默认所有模型先走 OpenAI 兼容路径：`/v1/chat/completions`
- 仅 Claude 系列在某个维度 `FAIL` 时，自动 fallback 到 Anthropic 原生：`/v1/messages`
- 输出单项检查结果和最终兼容矩阵

## 覆盖范围

- 模型：`gpt-5.4`、`gpt-4o`、`claude-4.6-opus`、`claude-4.6-sonnet`、`deepseek-r1`、`gemini-3.1-pro-preview`、`gemini-2.5-flash`、`qwen3.5-plus`、`kimi-k2.5`
- 维度：`D1-D7`
- 状态：
  - `PASS`：OpenAI 路径通过
  - `PASS(fallback)`：OpenAI 路径失败，Anthropic 原生补跑通过
  - `PARTIAL`：请求成功，但检查项未全部满足
  - `FAIL`：请求失败，或检查项完全不满足

## 环境变量

复用根目录 `.env`：

```env
OPENAI_API_KEY=...
OPENAI_API_BASE=...
```

说明：

- `OPENAI_API_BASE` 预期是 OpenAI 兼容基址，通常类似 `http://host:port/v1`
- 脚本会自动从这个地址推导 Anthropic fallback 的网关根地址

## 运行

```bash
cd rd-gateway-model-test-codex
python gateway_compat_test.py
python gateway_compat_test.py --model gpt-5.4
python gateway_compat_test.py --model claude-4.6-sonnet --dim D3
python gateway_compat_test.py --model gpt-4o,deepseek-r1 --dim D1,D2,D7
python gateway_compat_test.py --output-json result.json
```

## 实现说明

- `D1` 基础文本生成
- `D2` 流式输出
- `D3` 单工具调用
- `D4` 多工具并行调用
- `D5` 工具结果回传闭环
- `D6` 复杂参数 schema
- `D7` 多轮上下文保持

流式测试使用 `httpx` 直接校验 SSE chunk；普通请求走 `openai` 和 `anthropic` SDK。
