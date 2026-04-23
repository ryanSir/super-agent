## Why

当前项目已经具备较完整的后端、前端、流式协议、技能、沙箱、记忆、监控等实现，但缺少一张可持续维护的“全局技术架构图”来统一表达系统边界、核心组件、关键依赖和主数据流。现有零散文档和临时绘图难以同时满足完整性、风格一致性和后续迭代更新的要求。

现在需要引入一套稳定的图表产出方式，基于 `fireworks-tech-graph` 生成一张覆盖当前项目所有关键技术组件的全局架构图，并统一采用 Claude 官方风格，便于架构评审、对外展示和后续文档复用。

## What Changes

- 新增一项“项目级技术架构图”交付能力，定义完整全局图必须覆盖的层次、组件和依赖关系
- 使用 `fireworks-tech-graph` 作为唯一生成工具，输出 Claude 官方风格的 SVG 和 PNG 架构图
- 为当前仓库补充一份结构化图表源数据文件，确保架构图可重复生成、可修改、可校验
- 约束全局图必须包含前端层、网关与状态层、编排与能力层、执行与外部运行时层，以及核心存储与外部依赖
- 约束图中必须体现主请求链路、流式事件链路、Redis/Memory 写回链路、LLM/Skill/MCP/Sandbox 依赖关系
- 补充架构图生成与校验流程，要求输出产物位于项目文档目录并可由脚本重新导出

## Non-goals

- 不在本次变更中新增前端业务功能或后端运行时能力
- 不修改 Worker 风险分级，也不新增 SAFE/DANGEROUS Worker
- 不在本次变更中实现多张拆分图、时序图、部署图或交互式 HTML 浏览器
- 不调整现有系统实现逻辑，仅补充技术架构表达与交付规范
- 不将 draw.io 作为主生成工具，本次仅以 `fireworks-tech-graph` 为标准产出方案

## Capabilities

### New Capabilities

- `architecture-diagram`: 定义项目级全局技术架构图的覆盖范围、风格约束、产物格式、目录位置和校验要求，确保可以稳定生成一张完整的 Claude 官方风格全局架构图

### Modified Capabilities

- `skills`: 增加对 `fireworks-tech-graph` 作为项目内架构图生成工具的使用约束和产物交付要求

## Impact

- `doc-arch/` — 新增结构化图表源文件以及最终导出的 SVG/PNG 架构图
- `openspec/changes/generate-complete-architecture-diagram/` — 新增 proposal、design、specs、tasks 变更产物
- `openspec/specs/skills.md` — 需要补充技能驱动型文档产物的规范要求
- `openspec/changes/generate-complete-architecture-diagram/specs/architecture-diagram/spec.md` — 新增架构图能力规格
- `fireworks-tech-graph` skill 使用流程 — 需要明确模板、风格、导出和校验步骤

## Implementation Status

- 已生成正式组件清单：`doc-arch/fireworks-tech-graph-architecture-components.md`
- 已生成正式源文件：`doc-arch/fireworks-tech-graph-architecture-complete-style6.json`
- 已生成正式产物：`doc-arch/fireworks-tech-graph-architecture-complete-style6.svg` 与 `doc-arch/fireworks-tech-graph-architecture-complete-style6.png`
- 当前产物已 ready，可作为项目正式全景技术架构图使用
