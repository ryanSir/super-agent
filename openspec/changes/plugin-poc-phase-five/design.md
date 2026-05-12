## Context

当前示例插件包含 OpenAPI capability：

```yaml
capabilities:
  openapi:
    - name: slack-demo-api
      spec: openapi/slack.yaml
```

Phase 5 让该 capability 可以通过 gateway 调用，但 runtime 使用 mock transport，避免网络、认证和外部服务不稳定。

## Goals / Non-Goals

**Goals:**

- 读取 OpenAPI spec。
- 根据 `operation_id` 找到 method/path。
- 返回 mock HTTP result。
- 沿用 credential/policy/audit 链路。

**Non-Goals:**

- 不实现真实 HTTP。
- 不实现完整 OpenAPI request builder。
- 不实现 response schema 校验。

## Decisions

### Decision 1: input 使用 `operation_id`

OpenAPI capability 本身表示一个 API spec。调用时通过 input 指定 operation：

```json
{
  "operation_id": "listMessages",
  "parameters": {}
}
```

### Decision 2: mock HTTP transport 返回 method/path/operation

输出结构：

```json
{
  "message": "mock openapi invocation succeeded",
  "operation_id": "listMessages",
  "method": "GET",
  "path": "/messages",
  "parameters": {}
}
```

### Decision 3: OpenAPI capability 也经过 policy/audit

虽然现在不做真实调用，但仍保留治理链路，确保后续真实 runtime 不绕过 credential 和审计。

## Risks / Trade-offs

- [Risk] mock transport 不能证明真实 API 调用可用 → Phase 5 只验证 runtime 插入点，后续再做真实 HTTP adapter。
- [Risk] operation 参数校验不足 → 后续引入更完整 OpenAPI parser 或现成库。
- [Risk] OpenAPI capability 粒度和 operation capability 粒度需要取舍 → 当前先按 spec capability + operation_id 调用，后续可生成 operation-level capabilities。

## Migration Plan

无迁移。新增 runtime 模块和测试。

