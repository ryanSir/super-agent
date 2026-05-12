# Phase 3：Tool Invocation Gateway 使用说明

## 当前能力

注意：当前仓库代码已经是 Phase 1-11 的集成态。Phase 4 之后，Credential、Policy、Audit 已经接入统一 `invoke` 链路，所以手动执行本阶段命令时，需要先配置 credential；对于 `send_message` 这种 sensitive action，还需要加 `--confirm-sensitive`。

也就是说，Phase 3 关注的是 Tool Invocation Gateway 的调用协议和结果结构；Phase 4 负责解释为什么会出现 `missing_credential`、`sensitive_action_requires_confirmation` 等治理类错误。

Phase 3 在 Phase 2 的基础上新增：

```text
publish -> install -> enable -> list-capabilities -> invoke
```

当前可以验证：

- 通过 `capability_id` 调用已启用的 tool capability。
- 根据 tool 的 `input_schema.required` 校验必填输入。
- 返回统一 Invocation Result。
- 对不存在的 capability 返回明确错误。

Phase 3 初始开发时暂不覆盖：

- 真实 OpenAPI HTTP 调用。
- 真实 MCP 调用。
- Credential Broker。
- Policy Engine。
- Agent Runtime 主链路接入。

这些能力已经在后续 Phase 4-11 中逐步接入。当前再执行本阶段文档时，应按“最终集成态”理解。

## 新增文件说明

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/core/gateway.py` | Tool Invocation Gateway，负责查找 capability、校验 input、调用 runtime 并返回统一结果 |

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

PYTHONPATH=plugin-poc python -m plugin_poc.cli configure-credential company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --values '{"client_id":"demo-client","client_secret":"demo-secret"}'
```

## 2. 调用 tool capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --confirm-sensitive \
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
  --user user_001 \
  --confirm-sensitive \
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

## 4. 验证不存在的 capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.not_exists \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "capability_not_found"
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

当前集成态中，Gateway 前后已经接入：

```text
Credential Broker / Policy Engine
  ↓
Tool Invocation Gateway
  ↓
OpenAPI Runtime / MCP Runtime
  ↓
Audit / Observability
```

所以如果你只想验证 Phase 3 的网关成功路径，需要先完成 credential 配置，并在 sensitive action 调用时加 `--confirm-sensitive`。如果你想验证治理失败路径，按 `phase-4-credential-policy-audit.md` 执行即可。
