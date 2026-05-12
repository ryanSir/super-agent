## Why

当前仓库已经完成 Plugin 能力规划文档，需要进入开发验证阶段。第一期先在现有 Agent POC 项目中新增独立 `plugin-poc/` 子目录，跑通插件规范、校验、打包、发布到本地 Registry 的最小闭环，为后续 Plugin Manager、Runtime Host 和 Agent 调用链路提供基础。

## What Changes

- 新增 `plugin-poc/` 独立 POC 目录，不侵入现有 `src_deepagent/` 主流程。
- 定义 `plugin.yaml` 的第一版 schema，并实现 manifest 校验能力。
- 支持通过 `path` 引用 tools、skills、credentials、openapi、data_sources 等子配置。
- 实现 `plugin validate`：校验 manifest、必填字段、枚举值、semver、路径引用和子配置基本结构。
- 实现 `plugin package`：生成 zip 插件包、manifest snapshot、checksums 和 package metadata。
- 实现 `plugin publish`：发布插件包到本地文件型 Registry。
- 提供一个示例插件，覆盖 tool、skill、credential、openapi 和 data source 声明。
- 提供基础测试，验证 validate/package/publish 的成功和失败场景。

## Non-goals

- 不实现真实 Plugin Runtime Host、daemon、sidecar 或 serverless 执行。
- 不接入现有 Agent Runtime 的实际 tool invocation 主链路。
- 不实现 MCP/OpenAPI 的真实远程调用。
- 不实现完整 Admin Console。
- 不实现外部 marketplace、签名、安全扫描和灰度发布。
- 不新增 Worker，因此本期无新增 SAFE/DANGEROUS Worker 风险等级。

## Capabilities

### New Capabilities

- `plugin-packaging`: 定义并实现插件 manifest 校验、插件打包和发布到本地 Registry 的最小能力。

### Modified Capabilities

- 无。

## Impact

- 新增代码目录：`plugin-poc/`
- 新增 OpenSpec 变更：`openspec/changes/plugin-poc-phase-one/`
- 新增本地示例插件和测试数据。
- 对现有 Agent Runtime、前端、Worker、Skill 主目录无直接运行时影响。
