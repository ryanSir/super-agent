# Plugin 文档存放说明

## 目的

本文说明 `doc-plugin` 目录下各类文档的存放规则，避免规划文档、汇报文档、POC 文档和阶段操作手册混在一起。

当前原则：

- Plugin 相关 Markdown 文档统一放在 `doc-plugin`。
- `plugin-poc` 只保留 POC 代码、schema、测试和示例插件包。
- 示例插件内的 `SKILL.md` 属于插件包内容，不作为说明文档迁移。
- 重要汇报和方案文档放在 `doc-plugin` 根目录。
- 模块级阶段操作手册放在 `doc-plugin/poc-phases/`。
- 生产化详细设计、模块开发计划、开源深度分析和当前 Agent 集成测试计划放在 `doc-plugin/development-plan/`。

## 根目录核心文档

这些文档是评审、汇报和方案讨论的主要入口，直接放在 `doc-plugin` 根目录。

| 文件 | 定位 |
| --- | --- |
| `01-plugin-platform-technical-director-report.md` | 面向技术负责人的完整汇报报告 |
| `02-plugin-capability-plan.md` | Plugin 能力规划总览 |
| `03-plugin-end-to-end-flow.md` | Plugin 端到端流程说明 |
| `04-poc-acceptance-and-roadmap.md` | POC 验收说明、阶段分层和生产化 Roadmap |
| `05-code-structure-and-deployment-mapping.md` | POC 代码分层与未来部署边界映射 |
| `06-plugin-poc-guide.md` | POC 使用指南和阶段文档索引 |
| `README.md` | 文档总索引 |
| `99-document-organization.md` | 当前文档存放说明 |

## 前期设计文档

这些文档是主方案的专项拆解，统一放在 `doc-plugin/design/`。

| 文件 | 定位 |
| --- | --- |
| `design/01-plugin-concept.md` | Plugin 概念定义、边界和命名 |
| `design/02-capability-and-manifest.md` | 能力模型和 manifest 草案 |
| `design/03-runtime-architecture.md` | Runtime 架构、管理面和调用面 |
| `design/04-mcp-openapi-strategy.md` | MCP / OpenAPI 双协议接入策略 |
| `design/05-mvp-roadmap.md` | MVP 范围和路线图 |
| `design/06-open-source-reference-and-reuse.md` | 开源参考、复用策略和源码调研计划 |
| `design/07-development-plan-and-estimation.md` | 0-1 开发计划和粗估 |

## 图表文件

图表源文件和导出图保留在 `doc-plugin` 根目录，因为它们被多个文档直接引用。

| 文件 | 定位 |
| --- | --- |
| `plugin-end-to-end-flow-swimlane.drawio` | 端到端流程泳道图源文件 |
| `plugin-end-to-end-flow-swimlane.svg` | 端到端流程泳道图导出文件 |
| `plugin-runtime-architecture.svg` | Plugin Runtime 架构图 |

## POC 阶段操作手册

阶段操作手册统一放在 `doc-plugin/poc-phases/`。

| 文件 | 定位 |
| --- | --- |
| `phase-1-packaging-registry.md` | 插件规范、校验、打包、发布 |
| `phase-2-install-enable-capabilities.md` | 安装、启用、Capability Index |
| `phase-3-tool-invocation-gateway.md` | Tool Invocation Gateway |
| `phase-4-credential-policy-audit.md` | Credential、Policy、Audit |
| `phase-5-openapi-runtime.md` | OpenAPI Runtime |
| `phase-6-mcp-runtime.md` | MCP Runtime |
| `phase-7-skill-runtime.md` | Skill Runtime |
| `phase-8-data-source-runtime.md` | Data Source Runtime |
| `phase-9-runtime-host-stdio-adapter.md` | Runtime Host 与 stdio adapter |
| `phase-10-observability-runtime-hardening.md` | Observability 与 Runtime 稳定性 |
| `phase-11-e2e-acceptance.md` | E2E 验收 |

## 生产化开发规划

生产化开发规划统一放在 `doc-plugin/development-plan/`，用于承接 POC 结论，进入详细设计和模块开发阶段。

| 文件 / 目录 | 定位 |
| --- | --- |
| `development-plan/README.md` | 生产化开发规划入口 |
| `development-plan/00-stage-transition.md` | 从 POC 到生产开发的阶段转换说明 |
| `development-plan/01-module-development-plan.md` | 模块开发总计划 |
| `development-plan/02-current-agent-integration-test-plan.md` | 当前 `src_deepagent` 集成测试计划 |
| `development-plan/03-open-source-deep-dive-plan.md` | 开源项目深度分析计划 |
| `development-plan/modules/` | 后续模块详细设计 |
| `development-plan/open-source-deep-dive/` | 候选开源项目深度分析 |

## `plugin-poc` 目录保留内容

`plugin-poc` 目录只保留可运行内容：

| 路径 | 定位 |
| --- | --- |
| `plugin_poc/` | POC 代码主体 |
| `schemas/` | manifest JSON Schema |
| `examples/slack-demo/` | 示例插件包 |
| `tests/` | 自动化测试 |

其中 `examples/slack-demo/skills/summarize-channel/SKILL.md` 是示例插件的一部分，必须留在插件包目录下，否则 Skill Runtime 和打包校验会受影响。

## 可清理内容

以下内容不属于有效文档或代码，可以保持删除或清理：

| 路径 | 说明 |
| --- | --- |
| `doc-plugin/.DS_Store` | macOS 临时文件 |
| `plugin-poc/**/__pycache__/` | Python 缓存 |
| `doc-plugin/assets/17784821471088.jpg` | 未被引用的历史图片 |
| `doc-plugin/assets/plugin-end-to-end-flow-swimlane.drawio.svg` | 未被引用的重复导出文件 |
| `doc-plugin/plugin-end-to-end-flow-swimlane.drawio.svg` | 未被引用的重复导出文件 |
