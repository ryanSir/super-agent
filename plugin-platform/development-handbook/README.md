# Plugin Platform 开发手册

本文档集面向两类读者：

- Plugin Platform 开发者：理解平台内部模块边界、代码流程、测试方式和后续扩展点。
- 插件接入团队：理解如何编写插件、发布插件、申请启用能力，以及业务 Agent 如何发现和调用插件能力。

## 文档结构

| 阶段 | 文档 | 主题 |
| --- | --- | --- |
| 总览 | `00-execution-chain.md` | 统一执行链路和本地验证入口 |
| M1 | `01-manifest-package-contract.md` | 插件包开发手册：manifest、目录规范、校验、发布 |
| M2 | `02-install-enable-capability-index.md` | 插件安装启用手册：install、enable、capability index |
| M3 | `03-runtime-loading-boundary.md` | 运行时加载边界：后台管理、桌面端和 Web Agent |
| M4 | 待补 | OpenAPI / MCP / Skill Runtime 调用 |
| M5 | 待补 | 端到端测试和发布验收 |
| M5.5 | 待补 | 当前 Agent 作为外部消费者接入 |
| M6 | 待补 | Policy、Credential、Audit 治理 |

## 编写约定

每个阶段文档固定包含：

1. 本阶段目标和边界。
2. 本阶段执行链路。
3. 对外契约。
4. 关键代码入口。
5. 主流程时序。
6. 失败路径。
7. 测试和验收方式。
8. 后续扩展点。
