# Phase 6：Streamable HTTP MCP Runtime 使用说明

## 当前能力

Phase 6 新增 Streamable HTTP MCP Runtime：

```text
MCP capability
  ↓
Streamable HTTP JSON-RPC
  ↓
SSE/JSON response parser
  ↓
统一 Invocation Result
```

当前支持：

- `mcp-list-tools`：直接从 MCP endpoint 获取 tools/list。
- `invoke` MCP capability：通过 `tool_name` 和 `arguments` 调用 `tools/call`。
- 解析 `text/event-stream` 响应中的 `data:` JSON-RPC。
- 沿用 credential、policy、audit 链路。

当前仍不支持：

- MCP session 持久化。
- OAuth / bearer token 注入。
- stdio MCP adapter。
- MCP resources/prompts。
- 长连接流式增量事件处理。

## 真实 MCP 地址

当前示例插件使用你提供的 Streamable HTTP MCP 地址：

```text
https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw?APP_ID=Patsnap
```

对应 manifest：

```yaml
capabilities:
  mcp:
    - name: eureka-claw-mcp
      transport: streamable_http
      url: https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw?APP_ID=Patsnap
```

## 1. 直接验证 MCP tools/list

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli mcp-list-tools \
  --endpoint 'https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw?APP_ID=Patsnap'
```

预期返回：

```json
{
  "status": "ok",
  "tools": [
    {
      "name": "...",
      "description": "...",
      "inputSchema": {}
    }
  ]
}
```

## 2. 准备插件状态和 credential

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

## 3. 查询启用后的 MCP capability

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-capabilities \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

预期能看到：

```text
company.slack-demo.mcp.eureka-claw-mcp
```

## 4. 调用 MCP capability

调用时 input 需要包含：

```json
{
  "tool_name": "具体 MCP tool 名称",
  "arguments": {}
}
```

示例：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.mcp.eureka-claw-mcp \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"tool_name":"ls_clinical_trial_search","arguments":{"disease":["non-small cell lung cancer"],"limit":1}}'
```

成功时 runtime 为：

```json
{
  "runtime": "streamable_http_mcp"
}
```

## 5. Phase 6 的边界

Phase 6 完成的是：

```text
Streamable HTTP MCP endpoint
  ↓
tools/list / tools/call
  ↓
SSE JSON-RPC parser
  ↓
Gateway Invocation Result
```

后续真实平台需要继续补：

- MCP initialize / session 管理策略。
- MCP tool schema 同步到 Capability Index。
- stdio MCP adapter 或 mcpo 集成。
- OAuth / API token 注入。
- 流式事件和长任务处理。

