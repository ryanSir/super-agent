## Why

Phase 1 已完成插件校验、打包和本地 Registry 发布，但插件发布后还不能被安装、启用或让 Agent 发现能力。Phase 2 需要补齐 Plugin Manager 和 Capability Index 的最小闭环，让插件从 Registry 进入“已安装、已启用、可发现”的状态。

## What Changes

- 新增 Plugin Manager 模块，支持从本地 Registry 安装插件包。
- 支持启用、禁用、卸载已安装插件。
- 新增 Capability Index，解析已启用插件的 tools、skills、openapi、mcp、data_sources 能力。
- 新增 Capability Resolver，按 workspace/agent 查询可用能力。
- 扩展 CLI：
  - `install`
  - `enable`
  - `disable`
  - `uninstall`
  - `list-installed`
  - `list-capabilities`
- 新增 Phase 2 使用文档和测试。

## Non-goals

- 不执行插件 runtime。
- 不调用 OpenAPI/MCP 真实外部服务。
- 不实现 credential 配置和 test connection。
- 不实现 Policy Engine 和权限校验。
- 不接入现有 Agent Runtime 主链路。
- 不新增 Worker，因此本期无新增 SAFE/DANGEROUS Worker 风险等级。

## Capabilities

### New Capabilities

- `plugin-installation`: 从本地 Registry 安装、启用、禁用、卸载插件，并生成 Agent 可查询的能力索引。

### Modified Capabilities

- `plugin-packaging`: 扩展 CLI 使用链路，让 Phase 1 发布的 Registry 包可以被 Phase 2 安装和启用。

## Impact

- 修改 `plugin-poc/plugin_poc/cli.py`
- 新增 `plugin-poc/plugin_poc/manager.py`
- 新增 `plugin-poc/plugin_poc/capability.py`
- 新增 `plugin-poc/phase-2-install-enable-capabilities.md`
- 新增/扩展测试覆盖 install/enable/disable/list-capabilities。
