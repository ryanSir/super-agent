# Phase 4：Credential、Policy 与 Audit 使用说明

## 当前能力

Phase 4 在 Phase 3 的 `invoke` 链路前后加入治理能力：

```text
Credential Broker
  ↓
Policy Engine
  ↓
Tool Invocation Gateway
  ↓
Audit Log
```

当前可以验证：

- 配置 plugin credential。
- list credential 时隐藏 secret 字段。
- invoke 前检查 credential 是否存在。
- sensitive action 需要显式 `--confirm-sensitive`。
- 每次 invoke 成功或失败都会写 audit log。

当前仍不支持：

- 生产级 KMS/加密。
- OAuth 浏览器授权和 refresh token。
- 完整 RBAC/ABAC。
- 真实 OpenAPI/MCP 调用。

注意：当前 secret 字段使用 `POC:<base64>` 本地编码，只用于 POC，不是生产安全方案。

## 新增文件说明

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/core/credentials.py` | POC Credential Broker，配置、查询、测试 credential |
| `plugin_poc/core/policy.py` | POC Policy Engine，检查 credential 是否存在和 sensitive action 是否确认 |
| `plugin_poc/core/audit.py` | 本地 audit log，记录每次 invoke 尝试 |

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

## 2. 未配置 credential 时调用

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"channel_id":"C001","text":"hello"}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "missing_credential"
  }
}
```

## 3. 配置 credential

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli configure-credential company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --values '{"client_id":"demo-client","client_secret":"demo-secret"}'
```

查看 credential：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-credentials \
  --state /tmp/plugin-poc-state
```

预期 `client_secret` 被隐藏：

```json
{
  "client_id": "demo-client",
  "client_secret": "***"
}
```

测试 credential 是否存在：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli test-credential company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001
```

## 4. 敏感操作需要确认

示例插件把 `send_message` 声明为 sensitive action。

配置 credential 后，如果不加 `--confirm-sensitive`：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"channel_id":"C001","text":"hello"}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "sensitive_action_requires_confirmation"
  }
}
```

加上确认：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --confirm-sensitive \
  --input '{"channel_id":"C001","text":"hello"}'
```

预期成功。

## 5. 查看 Audit Log

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-audit \
  --state /tmp/plugin-poc-state
```

Audit 记录包含：

- `created_at`
- `capability_id`
- `workspace`
- `agent`
- `user`
- `success`
- `error_code`
- `input_keys`
- `duration_ms`

Audit 不记录 credential secret，也不记录完整 input 值，只记录 input keys。

## 6. Phase 4 的边界

Phase 4 完成的是：

```text
已启用 capability
  ↓
credential 存在性检查
  ↓
sensitive action 确认检查
  ↓
mock invoke
  ↓
audit log
```

后续真实平台需要替换：

- 本地 JSON credential -> KMS/Secrets Manager/数据库
- POC policy -> 企业权限系统
- JSONL audit -> 结构化审计日志/可观测平台
- mock runtime -> OpenAPI/MCP Runtime
