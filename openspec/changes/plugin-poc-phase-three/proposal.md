## Why

Phase 2 已经让插件能力可以被安装、启用和发现，但能力仍然不能被调用。Phase 3 需要新增最小 Tool Invocation Gateway，让已启用的 tool capability 可以通过统一入口被调用，并为后续 OpenAPI/MCP Runtime 接入建立调用协议。

## What Changes

- 新增 Tool Invocation Gateway。
- 新增本地模拟 Tool Runtime，用于调用 Phase 2 中解析出的 `tool` capability。
- 支持基于 `capability_id + input + workspace + agent` 发起调用。
- 对 tool input 做 required 字段校验。
- 返回统一调用结果结构：success、capability_id、runtime、output、error、duration_ms。
- 新增 CLI：
  - `invoke`
- 对非 tool 能力返回明确错误，避免误以为 OpenAPI/MCP 已真实执行。
- 新增 Phase 3 使用文档和测试。

## Non-goals

- 不做真实 OpenAPI HTTP 调用。
- 不做真实 MCP 调用。
- 不做 Credential Broker。
- 不做 Policy Engine。
- 不接入现有 Agent Runtime 主链路。
- 不新增 Worker，因此本期无新增 SAFE/DANGEROUS Worker 风险等级。

## Capabilities

### New Capabilities

- `plugin-invocation`: 为已启用的插件 tool capability 提供统一调用入口和标准结果结构。

### Modified Capabilities

- `plugin-installation`: 复用 Phase 2 Capability Index 作为 invocation 的能力发现来源。

## Impact

- 新增 `plugin-poc/plugin_poc/gateway.py`
- 扩展 `plugin-poc/plugin_poc/cli.py`
- 新增 `plugin-poc/phase-3-tool-invocation-gateway.md`
- 新增测试覆盖 invoke 成功、缺 required 参数、能力不存在、能力类型不支持。
