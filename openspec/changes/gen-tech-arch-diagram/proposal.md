## Why

当前项目缺乏直观的技术架构可视化文档，新成员和协作方难以快速理解系统整体结构与组件关系。使用 fireworks-tech-graph 生成一套 Claude 官方风格的架构图，可作为项目的权威技术参考。

## What Changes

- 调用 `fireworks-tech-graph` skill 生成项目技术架构图（SVG + PNG 格式）
- 覆盖以下视角：系统整体架构、编排层与 Worker 层关系、数据流与 Streaming 通道、前端组件体系
- 输出文件存放至 `doc-arch/diagrams/` 目录
- 不修改任何源码，仅新增可视化文档资产

## Capabilities

### New Capabilities

- `tech-arch-diagram`: 使用 fireworks-tech-graph 生成 Super Agent 项目的多视角技术架构图，采用 Claude 官方配色与排版风格，输出 SVG + PNG

### Modified Capabilities

（无）

## Impact

- 新增文件：`doc-arch/diagrams/` 目录下若干 `.svg` / `.png` 图片
- 不影响任何运行时代码、API 或依赖
- Non-goals：不生成 C4 模型文档（已有 arch-doc/），不修改前端或后端源码，不引入新依赖