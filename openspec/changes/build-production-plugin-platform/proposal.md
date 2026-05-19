## Why

当前 `plugin-poc` 已经验证了 Plugin 作为能力封装单元的可行性，但它不是可生产部署的功能。下一步需要建设一个独立的 Plugin 平台，把插件开发、校验、打包、发布、安装、启用、能力索引和管理平台串成完整链路，并为后续接入当前 Agent 系统保留稳定边界。

## What Changes

- 新建独立的 `plugin-platform/` 工作区，避免污染现有 `src_deepagent` Agent 项目；当前仓库仅作为开发调试宿主，后续可迁移为独立项目。
- 建设生产级 Plugin 平台的一期骨架，覆盖开发侧、管理侧和调用侧边界：
  - 开发侧：`plugin.yaml` / 子配置、schema 校验、package、publish。
  - 管理侧：Registry、Plugin Manager、workspace/agent 级安装启用、Capability Index。
  - 调用侧：提供能力发现和调用入口，但暂不接入当前 Agent 主链路。
- 增加 Plugin 管理平台前端规划和一期页面骨架，用于插件列表、详情、版本、安装、启用和配置查看。
- 明确第一阶段只支持远程能力优先：
  - OpenAPI / HTTP 工具能力。
  - Streamable HTTP MCP 能力。
  - Skill Context 能力。
- 暂不实现 stdio MCP adapter 和完整 Runtime Host；相关能力仅保留后续扩展点。
- 对可复用开源框架按模块做深度分析，避免把 POC 整体替换成某个框架：
  - Codex Plugins / Dify：manifest、package layout、marketplace 经验。
  - MCP 官方 Streamable HTTP / Open WebUI：MCP 远程接入模型。
  - n8n：credential schema 和配置表单经验。
  - Dify plugin daemon：后续 Runtime Host 参考，不作为一期核心依赖。

## Non-goals

- 不在本变更中改造 `src_deepagent`、`frontend-deepagent` 或当前 Agent Runtime。
- 不把 `plugin-poc` 直接升级为生产实现；POC 仅作为需求和验证参考。
- 不在第一阶段开发 stdio MCP adapter、本地隔离 Runtime Host、任意脚本 hook、长驻 monitor、Workflow Plugin 或 Agent Strategy Plugin。
- 不在第一阶段实现完整企业级 IAM、细粒度 Policy、密钥托管、审计留存和 Langfuse 观测闭环；但需要预留接口和数据模型。

## Capabilities

### New Capabilities

- `plugin-platform-workspace`: 独立 Plugin 平台工作区、部署单元和模块边界。
- `plugin-developer-lifecycle`: 插件开发、校验、打包、发布的开发侧链路。
- `plugin-registry-manager`: 插件包存储、元数据注册、安装、启用和能力索引管理。
- `plugin-admin-console`: Plugin 管理平台前端的页面、状态和 API 契约。
- `plugin-capability-runtime`: 能力发现和远程调用边界，覆盖 OpenAPI、Streamable HTTP MCP 和 Skill Context。
- `plugin-open-source-reuse`: 各模块可参考或复用的开源框架评估准则。

### Modified Capabilities

- 无。本变更不修改现有 Agent、Worker、Skill、Streaming 或 A2UI 规格。

## Impact

- 新增 `plugin-platform/` 独立工作区，包含 backend、admin frontend、CLI/SDK、examples、tests 等模块。
- 新增 `doc-plugin/development-plan/` 下的生产化开发规划和开源框架深度分析文档。
- 新增 OpenSpec 规格与任务，用于约束第一阶段开发范围。
- 后续需要新增本地启动命令、测试命令和管理平台开发命令。
- 一期新增模块均视为平台服务或管理后台，不属于现有 Agent Worker；因此不涉及 SAFE/DANGEROUS Worker 风险等级变更。
