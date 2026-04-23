# Super Agent 架构文档

> 生成日期：2026-04-23 | 基于代码版本：agent-core-v2

## 文档导航

| 文档 | 内容 | 适合谁看 |
|------|------|---------|
| [01-system-context.md](01-system-context.md) | 系统定位、外部依赖、架构支柱全景 | 所有人，首先阅读 |
| [02-container-view.md](02-container-view.md) | 运行时进程/服务、通信协议、技术栈 | 运维、DevOps、新成员 |
| [03-component-view.md](03-component-view.md) | 模块职责、依赖关系、对外接口 | 后端开发者 |
| [04-runtime-flows.md](04-runtime-flows.md) | 请求链路、状态机、关键子流程时序 | 调试问题、理解执行逻辑 |
| [05-tech-decisions.md](05-tech-decisions.md) | 技术选型 ADR、架构约束 | 技术负责人、架构评审 |
| [06-deployment-guide.md](06-deployment-guide.md) | 环境要求、启动步骤、环境变量 | 部署、本地开发 |
| [07-directory-restructure.md](07-directory-restructure.md) | 目录重构方案、迁移映射 | 重构规划 |

## 建议阅读顺序

1. `01-system-context.md` — 建立全局视角
2. `02-container-view.md` — 理解运行时结构
3. `06-deployment-guide.md` — 跑起来
4. `03-component-view.md` — 深入模块细节
5. `04-runtime-flows.md` — 追踪请求链路
6. `05-tech-decisions.md` — 理解选型背后的权衡

## 项目状态

- 阶段：POC / 早期开发
- 后端：FastAPI + PydanticAI，核心编排链路已通
- 前端：React + Vite，A2UI 动态组件已实现
- 沙箱：本地模式（E2B_USE_LOCAL=true）可用，E2B Cloud 待接入
- 记忆/向量：Redis 已接入，Milvus 预留接口
