## Why

项目缺乏一张完整的全局技术架构图，新成员和协作方难以快速理解系统各组件之间的关系与数据流向。通过 fireworks-tech-graph 生成一张涵盖所有技术组件的全局架构图，以 Claude 官方风格呈现，提升项目可读性与沟通效率。

## What Changes

- 使用 `fireworks-tech-graph` skill 生成一张全局技术架构图（SVG + PNG）
- 架构图覆盖所有技术组件：前端、网关、编排层、Worker 层、工具/技能系统、存储、外部服务、可观测性
- 输出文件存放于 `doc-arch/` 目录
- 采用 Claude 官方视觉风格（配色、字体、布局规范）

## Non-goals

- 不生成多张分层图（仅一张全局图）
- 不修改任何源码或配置
- 不生成交互式/动态图表

## Capabilities

### New Capabilities

- `tech-arch-diagram`: 全局技术架构图，包含前端、API 网关、编排核心、Worker 执行层、工具/技能系统、存储层（Redis/Milvus）、外部 AI 服务（Anthropic/LiteLLM）、沙箱（E2B）、可观测性（Langfuse）等所有组件及其连接关系

### Modified Capabilities

（无）

## Impact

- 新增文件：`doc-arch/tech-arch-diagram.drawio`、`doc-arch/tech-arch-diagram.svg`、`doc-arch/tech-arch-diagram.png`
- 不影响任何运行时代码或配置
