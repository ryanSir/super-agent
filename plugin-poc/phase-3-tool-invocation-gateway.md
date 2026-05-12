# Phase 3：Tool Invocation Gateway 使用说明

## 当前能力

Phase 3 在 Phase 2 的基础上新增：

```text
publish -> install -> enable -> list-capabilities -> invoke
```

当前可以验证：

- 通过 `capability_id` 调用已启用的 tool capability。
- 根据 tool 的 `input_schema.required` 校验必填输入。
- 返回统一 Invocation Result。
- 对不存在的 capability 返回明确错误。
- 对非 tool capability 返回明确错误。

当前仍不支持：

- 真实 OpenAPI HTTP 调用。
- 真实 MCP 调用。
- Credential Broker。
- Policy Engine。
- Agent Runtime 主链路接入。

Phase 3 的 runtime 是 `local_mock_tool`，用于验证网关协议和调用边界。

## 新增文件说明

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/gateway.py` | Tool Invocation Gateway，负责查找 capability、校验 input、调用本地 mock runtime 并返回统一结果 |

## Invocation Result

成功结果：

```json
{
  "success": true,
  "capability_id": "company.slack-demo.tool.send_message",
  "runtime": "local_mock_tool",
  "output": {
    "message": "mock tool invocation succeeded"
  },
  "error": null,
  "duration_ms": 0
}
```

失败结果：

```json
{
  "success": false,
  "capability_id": "company.slack-demo.tool.send_message",
  "runtime": null,
  "output": null,
  "error": {
    "code": "invalid_input",
    "message": "missing required input fields: text"
  },
  "duration_ms": 0
}
```

## 1. 准备插件状态

```bash
rm -rf /tmp/plugin-poc-registry /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-registry \
  --force

PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

## 2. 调用 tool capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --input '{"channel_id":"C001","text":"hello"}'
```

预期成功：

```json
{
  "success": true,
  "capability_id": "company.slack-demo.tool.send_message",
  "runtime": "local_mock_tool"
}
```

## 3. 验证缺少必填输入

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --input '{"channel_id":"C001"}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "invalid_input"
  }
}
```

## 4. 验证非 tool capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.openapi.slack-demo-api \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --input '{}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "unsupported_capability_type"
  }
}
```

## 5. Phase 3 的边界

Phase 3 完成的是：

```text
Capability Index
  ↓
Tool Invocation Gateway
  ↓
local_mock_tool runtime
  ↓
统一 Invocation Result
```

Phase 4 之后才会继续做：

```text
Tool Invocation Gateway
  ↓
Credential Broker / Policy Engine
  ↓
OpenAPI Runtime / MCP Runtime
  ↓
真实外部系统调用
```

