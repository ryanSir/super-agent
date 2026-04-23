## Context

Super Agent 是一个企业级混合 AI Agent 引擎，包含前端（React/Vite）、API 网关（FastAPI）、编排层（PydanticAI）、多种 Worker、工具/技能系统、存储层（Redis/Milvus）、外部 AI 服务、沙箱（E2B）和可观测性（Langfuse）等众多组件。目前项目缺乏一张完整的全局技术架构图，需要通过 `fireworks-tech-graph` skill 生成。

## Goals / Non-Goals

**Goals:**
- 调用 `fireworks-tech-graph` skill，生成一张覆盖所有技术组件的全局架构图
- 采用 Claude 官方视觉风格（深色背景、品牌配色、清晰分层）
- 输出 SVG + PNG 双格式，存放于 `doc-arch/` 目录

**Non-Goals:**
- 不生成多张分层细节图
- 不修改任何源码或运行时配置
- 不生成交互式图表

## Decisions

**决策 1：使用 fireworks-tech-graph skill**
- 选择原因：该 skill 专为技术架构图设计，支持 SVG/PNG 导出，且支持自定义风格
- 备选方案：draw.io CLI（功能更强但需手动编写 XML，效率低）；Mermaid（不支持复杂布局和自定义风格）

**决策 2：单张全局图，分层布局**
- 布局分为 5 层：用户层 → 前端层 → 网关层 → 核心引擎层（编排+Worker+工具）→ 基础设施层（存储+外部服务+可观测性）
- 选择原因：单图便于整体理解，分层布局清晰展示数据流向

**决策 3：Claude 官方风格**
- 配色：深色背景（#1a1a2e），主色调使用 Claude 品牌橙色（#d97706）和蓝色（#3b82f6）
- 字体：清晰无衬线字体，组件名英文，层级标签中文

## Risks / Trade-offs

- [风险] fireworks-tech-graph 生成的图组件数量过多时可能布局拥挤 → 缓解：合理分组，使用泳道/容器框聚合同层组件
- [风险] 图中组件名称与实际代码路径不一致 → 缓解：严格对照 CLAUDE.md 中的源码结构填写组件名
