# Super Agent 架构文档

本目录包含 Super Agent 项目的完整架构文档，基于 C4 模型组织，从宏观到微观逐层展开。

## 文档索引

| 文档 | 内容 | 适合谁看 |
|------|------|----------|
| [01-system-context.md](./01-system-context.md) | C4 L1: 系统上下文 — Super Agent 与外部系统的关系 | 所有人 |
| [02-container-view.md](./02-container-view.md) | C4 L2: 容器视图 — 运行时进程、服务与通信协议 | 架构师、运维 |
| [03-component-view.md](./03-component-view.md) | C4 L3: 组件视图 — 后端 9 大支柱模块详解 | 开发者 |
| [04-runtime-flows.md](./04-runtime-flows.md) | 运行时数据流 — 核心链路时序图与状态机 | 开发者 |
| [05-tech-decisions.md](./05-tech-decisions.md) | 技术选型与决策记录 (ADR) | 架构师、新成员 |
| [06-deployment-guide.md](./06-deployment-guide.md) | 部署与配置指南 | 运维、开发者 |

## 建议阅读顺序

1. 先看 01 了解系统全貌和外部依赖
2. 再看 02 理解运行时架构和技术栈
3. 然后看 03 深入各模块职责和边界
4. 04 适合需要理解请求处理链路的开发者
5. 05/06 按需查阅

## 项目状态

当前处于第一个里程碑（MVP），核心功能已实现，后续将持续完善。本文档描述的是已实现的架构，不包含未落地的规划。

## 图表说明

所有架构图使用 Mermaid 语法，可在 GitHub、VS Code（Mermaid 插件）、JetBrains IDE 中直接渲染。
