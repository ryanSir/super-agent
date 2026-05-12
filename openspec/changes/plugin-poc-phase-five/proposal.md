## Why

Phase 4 已完成治理链路，但实际 runtime 仍然只有 local mock tool。Phase 5 需要让 `openapi` capability 进入调用链路，验证 API connector plugin 的核心路径：从 OpenAPI spec 解析 operation，并通过统一 gateway 返回标准调用结果。

## What Changes

- 新增 OpenAPI Runtime。
- 从已启用的 `openapi` capability 读取 OpenAPI spec。
- 支持通过 `operation_id` 选择 operation。
- 支持本地 mock HTTP transport，不发起外部网络请求。
- 扩展 `invoke` 支持 `openapi` capability。
- 保留 credential、policy、audit 链路。
- 新增 Phase 5 使用文档和测试。

## Non-goals

- 不做真实公网 HTTP 请求。
- 不做完整 OpenAPI 参数序列化。
- 不做 OAuth token 注入到真实请求。
- 不做 MCP Runtime。
- 不接入现有 Agent Runtime 主链路。
- 不新增 Worker，因此本期无新增 SAFE/DANGEROUS Worker 风险等级。

## Capabilities

### New Capabilities

- `plugin-openapi-runtime`: 为 OpenAPI capability 提供最小 operation 解析和 mock HTTP 调用能力。

### Modified Capabilities

- `plugin-invocation`: invoke 支持 `openapi` capability，并继续输出统一 Invocation Result。

## Impact

- 新增 `plugin-poc/plugin_poc/openapi_runtime.py`
- 修改 `plugin-poc/plugin_poc/gateway.py`
- 修改 `plugin-poc/examples/slack-demo/openapi/slack.yaml`
- 新增 `plugin-poc/phase-5-openapi-runtime.md`
- 新增测试覆盖 OpenAPI capability invoke。
