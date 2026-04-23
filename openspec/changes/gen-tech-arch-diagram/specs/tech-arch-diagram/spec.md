## ADDED Requirements

### Requirement: 生成系统整体技术架构图
系统 SHALL 调用 fireworks-tech-graph skill，基于项目源码结构生成 Super Agent 整体技术架构图，采用 Claude 官方风格（紫色主色 #7C3AED），输出 SVG + PNG 至 `doc-arch/diagrams/01-overall-arch.svg`。

#### Scenario: 成功生成整体架构图
- **WHEN** 调用 fireworks-tech-graph，传入项目根目录和"整体架构"视角参数
- **THEN** 在 `doc-arch/diagrams/` 下生成 `01-overall-arch.svg` 和 `01-overall-arch.png`，图中包含网关层、编排层、Worker 层、存储层四个分层

#### Scenario: 输出目录不存在
- **WHEN** `doc-arch/diagrams/` 目录不存在时触发生成
- **THEN** 自动创建目录后再写入文件，不报错退出

### Requirement: 生成编排与 Worker 关系图
系统 SHALL 生成聚焦于 Orchestrator → ReasoningEngine → AgentFactory → Workers 调用链的关系图，输出至 `doc-arch/diagrams/02-orchestrator-workers.svg`。

#### Scenario: 成功生成编排关系图
- **WHEN** 调用 fireworks-tech-graph，传入"编排与Worker"视角参数
- **THEN** 图中清晰展示 DIRECT/AUTO/PLAN_AND_EXECUTE/SUB_AGENT 四种执行模式的路由关系

#### Scenario: 组件名称与源码不一致
- **WHEN** skill 推断的组件名与实际模块名有偏差
- **THEN** 以源码中的实际类名/模块名为准，手动修正后重新导出

### Requirement: 生成 Streaming 数据流图
系统 SHALL 生成从 API 请求到 SSE 响应的完整数据流图，覆盖 Redis Stream 中转和断点续传机制，输出至 `doc-arch/diagrams/03-streaming-flow.svg`。

#### Scenario: 成功生成数据流图
- **WHEN** 调用 fireworks-tech-graph，传入"Streaming数据流"视角参数
- **THEN** 图中包含 Client → Gateway → Orchestrator → Worker → Redis Stream → SSE Client 的完整链路

#### Scenario: 断点续传场景标注
- **WHEN** 图中包含 SSE 通道
- **THEN** 断点续传（reconnect）路径 SHALL 用虚线或不同颜色标注，与正常流区分

### Requirement: 生成前端组件体系图
系统 SHALL 生成前端 A2UI 组件体系图，展示 SSEClient → MessageHandler → ComponentRegistry → 动态组件的渲染链路，输出至 `doc-arch/diagrams/04-frontend-components.svg`。

#### Scenario: 成功生成前端组件图
- **WHEN** 调用 fireworks-tech-graph，传入"前端组件体系"视角参数
- **THEN** 图中包含 ChatMessage、ToolResultCard、DataWidget 等核心组件节点

#### Scenario: 组件注册表完整性
- **WHEN** 图中展示 ComponentRegistry
- **THEN** 所有在 ComponentRegistry.tsx 中注册的组件 SHALL 在图中有对应节点