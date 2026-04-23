## 1. 准备工作

- [x] 1.1 创建输出目录 `doc-arch/diagrams/`
- [x] 1.2 确认 fireworks-tech-graph skill 可用（检查 skill/ 目录）

## 2. 生成整体架构图

- [ ] 2.1 调用 fireworks-tech-graph，视角：系统整体分层（网关→编排→Worker→存储），Claude 官方风格，输出 `doc-arch/diagrams/01-overall-arch.svg` + `.png`
- [ ] 2.2 验证图中包含四个分层：Gateway、Orchestrator、Workers、Storage

## 3. 生成编排与 Worker 关系图

- [ ] 3.1 调用 fireworks-tech-graph，视角：ReasoningEngine 四种模式路由 → AgentFactory → Native/Sandbox Worker，输出 `doc-arch/diagrams/02-orchestrator-workers.svg` + `.png`
- [ ] 3.2 验证图中展示 DIRECT/AUTO/PLAN_AND_EXECUTE/SUB_AGENT 四条路由路径

## 4. 生成 Streaming 数据流图

- [ ] 4.1 调用 fireworks-tech-graph，视角：Client → Gateway → Orchestrator → Worker → Redis Stream → SSE，输出 `doc-arch/diagrams/03-streaming-flow.svg` + `.png`
- [ ] 4.2 验证断点续传路径用虚线或不同颜色标注

## 5. 生成前端组件体系图

- [ ] 5.1 调用 fireworks-tech-graph，视角：SSEClient → MessageHandler → ComponentRegistry → 动态组件，输出 `doc-arch/diagrams/04-frontend-components.svg` + `.png`
- [ ] 5.2 验证 ComponentRegistry.tsx 中所有注册组件在图中有对应节点

## 6. 收尾

- [ ] 6.1 在 `doc-arch/diagrams/README.md` 中记录各图说明、生成日期和更新方式