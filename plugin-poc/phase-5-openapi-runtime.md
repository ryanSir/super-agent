# Phase 5：OpenAPI Runtime 使用说明

## 当前能力

Phase 5 新增最小 OpenAPI Runtime：

```text
OpenAPI capability
  ↓
operation_id
  ↓
mock OpenAPI Runtime
  ↓
统一 Invocation Result
```

当前可以验证：

- 调用 `openapi` capability。
- 从 OpenAPI spec 中查找 `operationId`。
- 返回 mock HTTP 调用结果。
- 继续经过 credential、policy、audit 链路。

当前仍不支持：

- 真实 HTTP 请求。
- 完整 OpenAPI 参数序列化。
- OAuth token 注入真实请求。
- response schema 校验。
- MCP Runtime。

## 新增文件说明

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/openapi_runtime.py` | 读取 OpenAPI spec，按 `operation_id` 查找 operation，并返回 mock OpenAPI 调用结果 |

## 1. 准备插件状态和 credential

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

## 2. 调用 OpenAPI capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.openapi.slack-demo-api \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"operation_id":"listMessages","parameters":{"limit":10}}'
```

预期成功：

```json
{
  "success": true,
  "runtime": "mock_openapi",
  "output": {
    "message": "mock openapi invocation succeeded",
    "operation_id": "listMessages",
    "method": "GET",
    "path": "/messages",
    "parameters": {
      "limit": 10
    }
  }
}
```

## 3. 验证缺少 operation_id

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.openapi.slack-demo-api \
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
    "code": "invalid_input"
  }
}
```

## 4. 验证未知 operation

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.openapi.slack-demo-api \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"operation_id":"missingOperation"}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "operation_not_found"
  }
}
```

## 5. Phase 5 的边界

Phase 5 完成的是：

```text
OpenAPI spec
  ↓
operation_id lookup
  ↓
mock OpenAPI invocation
  ↓
audit log
```

后续真实平台需要继续实现：

- OpenAPI operation-level capability 生成。
- HTTP request builder。
- credential/token 注入。
- timeout/retry/error mapping。
- response schema 校验。

