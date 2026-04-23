## Context

当前仓库已经同时存在多份架构文档、draw.io 产物、`fireworks-tech-graph` 技能安装记录，以及分散在 `src_deepagent/`、`frontend-deepagent/`、`doc-arch/`、`openspec/` 下的模块实现说明。问题不在于“没有信息”，而在于缺少一张统一、完整、可复生成的全局技术架构图。

此次设计的目标不是新增运行时能力，而是建立一套稳定的“架构图交付流程”：
- 从代码结构和已有架构文档提取组件清单
- 使用 `fireworks-tech-graph` 生成 Claude 官方风格的全局图
- 在单张图中覆盖所有关键技术组件
- 保持产物可重复生成、可校验、可持续更新

主要约束如下：
- 只生成一张全局图，不拆分多页
- 风格固定为 Claude 官方风格（style 6）
- 产物必须进入项目文档目录，不能停留在临时文件
- 图中必须体现前端、网关、编排、能力、执行、存储、监控、外部依赖
- 图不是任意美术图，而是工程级技术文档，必须可维护

## Goals / Non-Goals

**Goals:**
- 生成一张覆盖当前项目全部关键技术组件的全局技术架构图
- 明确主请求链路、SSE 流式链路、Redis/Memory 写回链路、LLM/Skill/MCP/Sandbox 依赖链路
- 使用 `fireworks-tech-graph` 的结构化 JSON 作为源文件，而不是直接手写不可维护的 SVG
- 输出可直接复用的 `.json + .svg + .png` 产物
- 建立完整性检查规则，避免图中遗漏关键模块

**Non-Goals:**
- 不在本次设计中替代所有现有架构文档
- 不生成部署拓扑图、时序图、数据流图、HTML 交互版
- 不引入新的后端 API 或前端组件来渲染这张图
- 不把 draw.io 产物作为主标准，仅保留其作为历史对照方案

## Decisions

### 1. 使用 `fireworks-tech-graph` 作为唯一标准产出工具

选择理由：
- 该技能天然面向技术图，直接输出高质量 SVG/PNG
- 支持结构化 JSON 输入，适合长期维护
- 支持模板、风格、校验脚本和 PNG 导出，交付链条完整

备选方案：
- `drawio-skill`
  - 优点：更容易人工微调
  - 缺点：图形自由度高但一致性差，线条和布局质量更依赖手工调整
- 手写 SVG
  - 优点：控制力最强
  - 缺点：维护成本过高，后续修改风险大

结论：
- 标准产出使用 `fireworks-tech-graph`
- draw.io 只作为对照和补充工具，不进入正式方案

### 2. 用单张“全局图”覆盖所有关键组件，但通过分层容器控制复杂度

选择理由：
- 用户明确要求只要一张全局图
- 单图最适合总体汇报和系统全景说明
- 通过分层容器可以在单图下维持一定的阅读秩序

设计方式：
- Client Layer
- Gateway + State Layer
- Orchestration + Capability Layer
- Execution + External Runtime Layer

备选方案：
- 拆成多张图
  - 可读性更高，但不符合本次“只要一张全局图”的要求

结论：
- 单图交付
- 通过容器、颜色语义和链路约束降低复杂度

### 3. 以“完整组件清单”驱动绘图，而不是凭印象选模块

选择理由：
- 当前项目模块较多，若仅凭主观取舍，容易遗漏 `SessionManager`、`SSEClient`、`MessageHandler`、`LLM Registry`、`Skill Registry`、`MCP Client Manager` 等中介组件
- 单张图必须优先保证覆盖面，再优化观感

组件清单至少覆盖：
- 前端：Browser UI、React App、SSEClient、MessageHandler / ResponseBlock
- 网关：main.py、rest_api.py、websocket_api.py
- 状态与流式：SessionManager、sse_endpoint.py、stream_adapter.py
- 编排：ReasoningEngine、AgentFactory、ContextBuilder
- 能力：Base Tools Router、LLM Registry、Sub-Agent Roles、Memory Manager、Skill/MCP Registry
- 执行：SandboxWorker、NativeWorker、Skills Directory、MCP Servers
- 基础设施：Redis、LLM APIs、Pi Agent/E2B、Langfuse + Metrics

备选方案：
- 只保留 8-10 个核心框
  - 更美观，但不满足“越完整越好”

结论：
- 先保证完整，再通过布局与连线减少混乱

### 4. 图表源数据使用项目内 JSON 文件持久化

选择理由：
- `fireworks-tech-graph` 的 `generate-from-template.py` 支持 JSON 输入
- JSON 更容易审阅、diff 和迭代
- 可作为后续持续更新架构图的单一事实来源

目录约定：
- `doc-arch/fireworks-tech-graph-architecture-complete-style6.json`
- `doc-arch/fireworks-tech-graph-architecture-complete-style6.svg`
- `doc-arch/fireworks-tech-graph-architecture-complete-style6.png`

结论：
- JSON 为源
- SVG/PNG 为派生产物

### 5. 校验分两层进行：语法可导出 + 视觉质量可接受

第一层：
- `validate-svg.sh`
- `rsvg-convert` 导出成功

第二层：
- 人工检查是否存在裁切、主链路断裂、关键标签遮挡、严重箭线碰撞

原因：
- 技术图生成脚本可以验证语法，但无法完全避免视觉上的局部拥挤
- 本次重点是“完整全局图”，允许轻微线碰撞，但不允许文件损坏、组件缺失或主链路不可读

## Risks / Trade-offs

- [单图信息量过大] → 通过分层容器、统一颜色语义、只保留关键链路来抑制复杂度
- [箭线碰撞依然存在] → 优先保证组件完整性；若冲突明显，再通过 route_points 进行二次调线
- [后续代码变更导致图过期] → 保留 JSON 源文件并将更新流程纳入文档维护
- [技能模板能力受限] → 允许在 JSON 布局层做更细的坐标和走线微调，而不是放弃模板化方案
- [过度追求美观导致遗漏模块] → 明确“完整性优先于纯展示感”

## Migration Plan

1. 建立变更产物，定义全局架构图范围和交付规则
2. 基于当前代码和文档梳理组件清单
3. 生成 `fireworks-tech-graph` JSON 源文件
4. 生成 SVG 和 PNG 产物并完成校验
5. 将产物固定在 `doc-arch/` 目录下，作为后续维护基线

回滚方式：
- 删除本次新增的 JSON/SVG/PNG 产物
- 保留原有 draw.io 架构图作为历史版本，不影响运行时代码

## Open Questions

- 是否需要在全局图中显式展示 `websocket_api.py`，还是只在 Gateway 节点说明中合并体现
- 是否需要把 `ComponentRegistry`、`ResponseBlock`、`TerminalView` 等前端组件继续下钻到单独节点
- 是否接受“完整全景图有少量连线碰撞但信息完整”，还是必须进一步压缩模块数量以换取观感
