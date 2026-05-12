## Why

Phase 3 已经跑通统一调用入口，但调用链路还没有企业治理能力。Phase 4 需要加入 POC 级 Credential Broker、Policy Engine 和 Audit Log，让插件调用具备凭据存在性检查、敏感操作确认和审计记录，为后续真实 OpenAPI/MCP Runtime 做准备。

## What Changes

- 新增 Credential Broker，本地保存 workspace/plugin 级 credential。
- 新增 credential schema 字段校验和 secret 字段本地编码存储。
- 新增 Policy Engine，在 invoke 前检查：
  - 插件是否需要 credential。
  - credential 是否已配置。
  - tool 是否属于 sensitive action。
  - sensitive action 是否已显式确认。
- 新增 Audit Log，每次 invoke 成功或失败都写入本地审计日志。
- 扩展 CLI：
  - `configure-credential`
  - `list-credentials`
  - `test-credential`
  - `list-audit`
  - `invoke --user --confirm-sensitive`
- 新增 Phase 4 使用文档和测试。

## Non-goals

- 不实现生产级 KMS/加密，当前仅做 POC 级本地编码存储。
- 不实现 OAuth 浏览器授权和 token refresh。
- 不实现完整 RBAC/ABAC 权限系统。
- 不做真实外部 API/MCP 调用。
- 不接入现有 Agent Runtime 主链路。
- 不新增 Worker，因此本期无新增 SAFE/DANGEROUS Worker 风险等级。

## Capabilities

### New Capabilities

- `plugin-governance`: 为插件调用提供 POC 级 credential 配置、敏感操作策略检查和审计记录。

### Modified Capabilities

- `plugin-invocation`: invoke 调用链路增加 credential、policy 和 audit 处理。

## Impact

- 新增 `plugin-poc/plugin_poc/credentials.py`
- 新增 `plugin-poc/plugin_poc/policy.py`
- 新增 `plugin-poc/plugin_poc/audit.py`
- 修改 `plugin-poc/plugin_poc/gateway.py`
- 修改 `plugin-poc/plugin_poc/cli.py`
- 新增 `plugin-poc/phase-4-credential-policy-audit.md`
- 新增测试覆盖 credential、policy、audit 和 invoke 治理链路。
