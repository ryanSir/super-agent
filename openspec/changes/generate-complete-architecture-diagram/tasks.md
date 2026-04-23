## 1. 架构信息梳理

- [x] 1.1 盘点 `frontend-deepagent/` 中需要进入全局图的前端组件节点，并形成固定组件清单
- [x] 1.2 盘点 `src_deepagent/gateway/`、`state/`、`streaming/` 中需要进入全局图的网关与状态节点
- [x] 1.3 盘点 `src_deepagent/orchestrator/`、`context/`、`capabilities/`、`agents/`、`memory/`、`llm/` 中需要进入全局图的编排与能力节点
- [x] 1.4 盘点 `workers/`、`skill/`、`MCP`、`Redis`、`LLM API`、`Langfuse`、`Pi Agent/E2B` 等执行与外部运行时节点

## 2. 图表源数据建模

- [x] 2.1 在 `doc-arch/fireworks-tech-graph-architecture-complete-style6.json` 中定义分层容器、节点位置和节点样式
- [x] 2.2 在同一 JSON 中定义主请求链路、SSE 链路、Redis/Memory 写回链路、LLM/Skill/MCP/Sandbox 依赖链路
- [x] 2.3 在同一 JSON 中补齐标题、副标题、图例和 Claude 官方风格配置

## 3. 图表生成与校验

- [x] 3.1 使用 `generate-from-template.py` 从 JSON 生成 `doc-arch/fireworks-tech-graph-architecture-complete-style6.svg`
- [x] 3.2 使用 `rsvg-convert` 导出 `doc-arch/fireworks-tech-graph-architecture-complete-style6.png`
- [x] 3.3 运行 `validate-svg.sh` 校验 SVG 语法、marker 引用和导出可用性
- [x] 3.4 针对裁切、标签遮挡和严重箭线碰撞调整 JSON 中的节点坐标和 route_points

## 4. 文档交付与验收

- [x] 4.1 确认 `doc-arch/` 下同时存在 JSON、SVG、PNG 三类正式产物
- [x] 4.2 人工核对全局图是否覆盖 proposal/spec 中要求的全部关键技术组件
- [x] 4.3 人工核对图中是否清晰体现主链路、流式链路、写回链路和外部依赖关系
- [x] 4.4 在变更说明中记录该架构图已 ready，可作为项目正式全景技术架构图使用
