## Context

Phase 2 生成的 `capability_index.json` 中已经包含 tool capability：

```json
{
  "capability_id": "company.slack-demo.tool.send_message",
  "type": "tool",
  "input_schema": {
    "required": ["channel_id", "text"]
  }
}
```

Phase 3 基于这个 capability index 做最小调用网关，不直接接真实外部系统。

## Goals / Non-Goals

**Goals:**

- 建立统一 invocation API。
- 验证 Agent 后续只需要传 `capability_id` 和 input，就能通过网关调用能力。
- 校验 tool input required 字段。
- 返回标准化结果，作为后续 Runtime 的统一协议。

**Non-Goals:**

- 不做真实 OpenAPI/MCP Runtime。
- 不做 credential 注入。
- 不做权限策略。

## Decisions

### Decision 1: Phase 3 只实现 local mock tool runtime

原因：当前重点是调用协议和网关边界，不是外部系统接入。真实 OpenAPI/MCP 调用会引入网络、认证和协议选型，放到后续阶段更稳。

### Decision 2: invocation 结果使用统一结构

统一结构：

```json
{
  "success": true,
  "capability_id": "...",
  "runtime": "local_mock_tool",
  "output": {},
  "error": null,
  "duration_ms": 1
}
```

失败也使用同一结构，便于后续 Agent Runtime 和 Observability 接入。

### Decision 3: 非 tool capability 明确拒绝

Phase 3 查询到 openapi/mcp/data_source/skill capability 时返回 unsupported error，避免文档和行为暗示这些能力已经真实可执行。

## Risks / Trade-offs

- [Risk] mock runtime 不代表真实业务调用 → 文档明确边界，Phase 4/后续再接 OpenAPI/MCP Runtime。
- [Risk] input schema 只校验 required → Phase 3 足够验证调用链路，后续引入完整 JSON Schema 校验。
- [Risk] Gateway 还没有 Policy/Credential → 后续阶段补齐，不在本期混入。

## Migration Plan

无迁移。新增独立模块和 CLI 命令。

