## ADDED Requirements

### Requirement: Project-wide complete architecture diagram
系统 SHALL 为当前项目生成一张单页的全局技术架构图，并使用 `fireworks-tech-graph` 的 Claude 官方风格作为标准输出风格。该架构图 MUST 覆盖前端层、网关与状态层、编排与能力层、执行与外部运行时层，以及关键存储与外部依赖。

#### Scenario: Generate complete single-page architecture diagram
- **WHEN** 系统为当前仓库生成正式技术架构图
- **THEN** 输出 MUST 为单张全局图，且图中 MUST 包含前端、网关、编排、能力、执行、存储、监控和外部系统

#### Scenario: Use Claude official style
- **WHEN** 技术架构图被生成
- **THEN** 输出 MUST 使用 `fireworks-tech-graph` 的 Claude 官方风格，而不是 draw.io 默认风格或其他随机主题

### Requirement: Complete component coverage
架构图 SHALL 显式覆盖当前项目的关键技术组件，而不是仅展示抽象层级。至少 MUST 包含 Browser UI、React App、SSE Client、A2UI Event Handler、FastAPI Gateway、Session Manager、Streaming Hub、Reasoning Engine、Agent Factory、Context Builder、Base Tools Router、LLM Registry、Sub-Agent Roles、Memory Manager、Skill + MCP Registry、Sandbox Worker、Native Worker、Skills Directory、MCP Servers、Redis、LLM APIs、Pi Agent/E2B、Langfuse + Metrics。

#### Scenario: Verify frontend component coverage
- **WHEN** 检查全局图的前端部分
- **THEN** 图中 MUST 同时出现 Browser UI、React App、SSE Client 和 A2UI Event Handler

#### Scenario: Verify orchestration component coverage
- **WHEN** 检查全局图的编排部分
- **THEN** 图中 MUST 同时出现 Reasoning Engine、Agent Factory、Context Builder 和 Base Tools Router

#### Scenario: Verify runtime and infrastructure coverage
- **WHEN** 检查全局图的执行与基础设施部分
- **THEN** 图中 MUST 同时出现 Sandbox Worker、Native Worker、Skills Directory、MCP Servers、Redis、LLM APIs、Pi Agent/E2B 和 Langfuse + Metrics

### Requirement: Key flow visibility
架构图 SHALL 明确表达至少四类关键链路：主请求/检索链路、规划与编排控制链路、Redis 或 Memory 写回链路、SSE 流式事件链路。

#### Scenario: Main request path is visible
- **WHEN** 用户阅读全局图的主流程
- **THEN** 图中 MUST 能看出从前端到网关，再到编排与能力层的主请求路径

#### Scenario: Streaming path is visible
- **WHEN** 用户查看流式响应链路
- **THEN** 图中 MUST 表达 Streaming Hub 到前端 SSE Client 的事件流方向

#### Scenario: Writeback path is visible
- **WHEN** 用户查看状态与记忆写回路径
- **THEN** 图中 MUST 表达 Session/Streaming/Memory 与 Redis 的写回关系

### Requirement: Reproducible source artifact
系统 MUST 使用项目内结构化 JSON 文件作为架构图源数据，并从该源文件生成 SVG 和 PNG。JSON、SVG、PNG 三类文件 MUST 一并保存在 `doc-arch/` 目录下。

#### Scenario: Source and outputs are stored together
- **WHEN** 架构图生成完成
- **THEN** `doc-arch/` 下 MUST 同时存在 JSON 源文件、SVG 文件和 PNG 文件

#### Scenario: Diagram can be regenerated
- **WHEN** 需要更新技术架构图
- **THEN** 开发者 MUST 能基于 JSON 源文件重新生成新的 SVG 和 PNG，而不是从零重画

### Requirement: Output validity
架构图产物 MUST 通过 SVG 基础校验和 PNG 导出校验，且不得出现文件损坏、标签不闭合或无法导出的情况。

#### Scenario: SVG passes syntax validation
- **WHEN** 对输出 SVG 执行校验脚本
- **THEN** SVG MUST 通过 XML 语法、标签平衡、marker 引用和闭合标签校验

#### Scenario: PNG export succeeds
- **WHEN** 使用 `rsvg-convert` 导出 PNG
- **THEN** 导出过程 MUST 成功完成，并产出可读取的 PNG 文件
