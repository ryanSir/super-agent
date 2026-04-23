## Context

Super Agent 是一个企业级混合 AI Agent 引擎，架构层次丰富（网关→编排→Worker→沙箱），目前缺乏可视化的技术架构图。本次变更通过调用 `fireworks-tech-graph` skill 生成多视角架构图，采用 Claude 官方配色风格，输出 SVG + PNG 供文档和演示使用。

## Goals / Non-Goals

**Goals:**
- 调用 `fireworks-tech-graph` skill 生成 Super Agent 完整技术架构图
- 覆盖：系统整体分层、编排与 Worker 关系、Streaming 数据流、前端组件体系
- 采用 Claude 官方风格（紫色主色调 #7C3AED，白底，圆角卡片，清晰层次）
- 输出 SVG + PNG 至 `doc-arch/diagrams/`

**Non-Goals:**
- 不修改任何后端/前端源码
- 不生成交互式图表（仅静态图片）
- 不替换已有 C4 文档（arch-doc/）

## Decisions

### 决策 1：使用 fireworks-tech-graph skill 而非手写 draw.io XML

**选择**：fireworks-tech-graph  
**理由**：skill 内置对技术架构图的语义理解，可直接从代码结构推断组件关系，无需手动维护 XML；输出格式为 SVG+PNG，可直接嵌入文档。  
**备选**：drawio-skill（需手写 XML，维护成本高）

### 决策 2：Claude 官方风格配色

**选择**：紫色主色 #7C3AED，辅色 #E9D5FF，背景白色，字体 Inter  
**理由**：与 Claude 品牌一致，适合对外展示和技术文档；对比度高，层次清晰。

### 决策 3：多视角分图而非单张全图

**选择**：生成 4 张分视角图（整体架构、编排层、数据流、前端）  
**理由**：单张全图信息密度过高，难以阅读；分图可按需引用，维护更灵活。

## Risks / Trade-offs

- [fireworks-tech-graph 输出质量依赖 skill 实现] → 若生成结果不符合预期，可手动调整 SVG 源文件
- [图片与代码可能随时间失同步] → 在 doc-arch/diagrams/README.md 中注明生成日期，定期更新