# Proposal: PydanticAI 原生 OTEL 接入 Langfuse 监控

## 背景

当前 Langfuse 集成存在根本性缺陷：所有 LLM 调用通过 PydanticAI 的 `OpenAIModel` + `OpenAIProvider` 直接打到网关，完全绕过了 LiteLLM。`setup_litellm()` 中注册的 `litellm.success_callback = ["langfuse"]` 永远不会触发，导致 Langfuse 面板无数据。

## 目标

利用 PydanticAI 1.70.0 原生支持的 OpenTelemetry instrumentation，将 Agent 运行、Tool 调用、LLM generation 全链路数据导出到 Langfuse 的 OTLP endpoint。

## 方案

PydanticAI Agent 支持 `instrument=True` 参数，会自动通过 OTEL SDK 上报 spans。Langfuse 提供标准 OTLP HTTP endpoint（`{host}/api/public/otel`），只需配置 `OTLPSpanExporter` 指向该地址即可，无需修改任何业务逻辑。

环境中已安装：
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-http`
- `logfire`（PydanticAI 推荐的 instrumentation 库，可选）

## Non-goals

- 不修改 LiteLLM 配置（LiteLLM 目前未参与实际 LLM 调用，保持现状）
- 不替换现有的 `langfuse_tracer.py` 手动 span（Worker 层的 span 继续保留）
- 不引入新的 Python 依赖（OTEL 相关包已安装）
- 不修改 Worker 执行逻辑
- 不修改前端代码
