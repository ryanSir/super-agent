# Plugin 规划文档

本目录用于沉淀 Agent 平台 Plugin 能力规划。当前文档包含规划总览、专项设计、端到端流程图和 POC 验收说明。

## 文档结构

| 文档 | 说明 |
| --- | --- |
| [01-plugin-platform-technical-director-report.md](./01-plugin-platform-technical-director-report.md) | 面向技术负责人的完整汇报报告 |
| [02-plugin-capability-plan.md](./02-plugin-capability-plan.md) | Plugin 能力规划总览草案 |
| [design/01-plugin-concept.md](./design/01-plugin-concept.md) | Plugin 概念定义、边界和命名 |
| [design/02-capability-and-manifest.md](./design/02-capability-and-manifest.md) | 能力模型、能力注册、manifest 草案 |
| [design/03-runtime-architecture.md](./design/03-runtime-architecture.md) | Plugin Runtime、管理面、调用面和架构图 |
| [design/04-mcp-openapi-strategy.md](./design/04-mcp-openapi-strategy.md) | MCP / OpenAPI 双协议接入策略 |
| [design/05-mvp-roadmap.md](./design/05-mvp-roadmap.md) | 第一版范围、二期路线图和本周产出 |
| [design/06-open-source-reference-and-reuse.md](./design/06-open-source-reference-and-reuse.md) | 开源项目参考、复用策略和源码调研计划 |
| [design/07-development-plan-and-estimation.md](./design/07-development-plan-and-estimation.md) | 0-1 开发计划、端到端流程、角色配置和粗估 |
| [03-plugin-end-to-end-flow.md](./03-plugin-end-to-end-flow.md) | Plugin 端到端流程泳道图、业务 Agent 交互和 POC 映射 |
| [04-poc-acceptance-and-roadmap.md](./04-poc-acceptance-and-roadmap.md) | Plugin POC 验收说明、部署边界和生产化 Roadmap |
| [05-code-structure-and-deployment-mapping.md](./05-code-structure-and-deployment-mapping.md) | Plugin POC 代码分层、泳道图映射和未来服务边界 |
| [06-plugin-poc-guide.md](./06-plugin-poc-guide.md) | Plugin POC 使用指南和阶段文档索引 |
| [poc-phases/](./poc-phases/) | Phase 1-11 模块级操作和验证说明 |
| [99-document-organization.md](./99-document-organization.md) | 文档存放分类和维护说明 |

## 当前建议

当前建议先基于概念、能力模型、运行时架构、协议策略、MVP 范围、开源复用策略、0-1 开发计划、端到端流程图和 POC 验收说明做一次完整评审。`design/07-development-plan-and-estimation.md` 中的估时为 ROM 粗估，用于资源判断和方案评审，不作为最终排期承诺。
