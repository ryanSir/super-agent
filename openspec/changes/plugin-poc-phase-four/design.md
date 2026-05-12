## Context

当前 POC 的 `invoke` 只校验 capability 和 input，不关注插件声明的 `auth`、`permissions` 和 `policy`。示例插件声明了 OAuth credential 和 sensitive action：

```yaml
auth:
  type: oauth2
  credential_schema: credentials/oauth.yaml
permissions:
  sensitive_actions:
    - send_message
```

Phase 4 将这些声明接入调用链路，但仍保持本地 POC 实现。

## Goals / Non-Goals

**Goals:**

- 支持配置和查询本地 credential。
- 支持基于 credential schema 校验必填字段。
- 支持 invoke 前的 credential 存在性检查。
- 支持 sensitive action 显式确认。
- 支持 audit log。

**Non-Goals:**

- 不做生产级加密。
- 不做 OAuth 授权码流程。
- 不做完整权限模型。

## Decisions

### Decision 1: 本地 credential 使用 POC 编码存储

secret 字段保存为 `POC:<base64>`。这不是安全加密，只用于验证 Broker 接口、字段分类和注入边界。

### Decision 2: policy 只做两类检查

Phase 4 只检查：

- plugin auth 不为 `none` 时是否已配置 credential。
- tool 名称在 `permissions.sensitive_actions` 中时是否传入 `--confirm-sensitive`。

后续再扩展 user/workspace RBAC、scope、read/write/action policy。

### Decision 3: audit log 记录输入摘要，不记录 secret

Audit Log 记录 capability_id、user、workspace、agent、success、error_code 和 input keys，不记录 credential 值。

## Risks / Trade-offs

- [Risk] POC 编码被误认为生产加密 → 文档明确禁止生产使用。
- [Risk] Policy 过于简化 → 只用于验证调用链路插入点，后续替换为真实 Policy Engine。
- [Risk] Audit 使用 JSON 文件不适合并发 → POC 可接受，后续迁移到数据库/日志系统。

## Migration Plan

无迁移。新增本地状态文件：

```text
credentials.json
audit_log.jsonl
```

