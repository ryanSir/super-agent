## Context

当前 `src_deepagent/` 是一个 POC 级别的智能体运行时，基于 pydantic-deepagents 构建。主流程（ReasoningEngine → AgentFactory → Workers）已跑通，但缺乏企业级所需的安全隔离、多用户支持、监控计费、前端产品、测试体系等能力。

现有技术栈：Python 3.12 + FastAPI + PydanticAI + Redis + E2B。前端计划采用 React 18 + TypeScript + Vite。

本设计覆盖从 POC 到企业级生产的完整技术方案，分三个 Phase 交付（核心引擎 → 产品形态 → 生态稳定）。

## Goals / Non-Goals

**Goals:**
- 构建生产级 Agent Runtime，支持四种执行模式的完整生命周期
- 实现安全沙箱隔离（Docker + K8s 双模式），保障代码执行安全
- 建立多用户权限体系和计费系统
- 提供完整的 Web + CLI + IM 多通道产品界面
- 构建 Skill + MCP 工具生态
- 实现全链路监控和 Agent Evaluation 体系
- 支撑 8-10 人团队 12-14 周交付

**Non-Goals:**
- 自研 LLM 或模型训练/微调
- 移动端 App
- 多集群跨区域部署
- Skill 自动生成
- 通用 AI 开发平台（只做 Agent 运行时）

## Decisions

### D1: Agent Runtime 架构 — PydanticAI + 自建 Middleware Pipeline

**选择**: 保持 PydanticAI 作为 Agent 执行引擎，自建 13-stage Middleware Pipeline 扩展能力。

**替代方案**:
- LangChain/LangGraph：生态丰富但抽象层过重，定制性差，性能开销大
- 纯自建：完全可控但开发量翻倍，且需要自己实现 tool calling、streaming 等基础能力
- CrewAI：多 Agent 协作好但单 Agent 能力弱，不适合四种模式切换

**理由**: PydanticAI 提供了 Agent 执行循环、工具调用、流式输出等基础能力，Middleware Pipeline 在此之上叠加权限检查、监控埋点、上下文压缩等企业级需求，两者职责清晰。

### D2: 沙箱引擎 — Docker + K8s 双模式

**选择**: 开发环境用 Docker 本地沙箱，生产环境用 K8s Pod 沙箱，统一 SandboxManager 接口。

**替代方案**:
- 纯 E2B 云沙箱：简单但成本高、延迟大、依赖外部服务
- 纯 Docker：开发友好但生产环境资源管理和调度能力不足
- gVisor/Firecracker：安全性更强但运维复杂度高

**理由**: Docker 模式零依赖适合开发调试，K8s 模式利用现有集群能力实现资源调度、自动扩缩、健康检查。Warm Pool 预热机制解决冷启动问题。E2B 保留为可选后端。

### D3: 记忆系统 — LanceDB 替换 Redis

**选择**: 用 LanceDB 实现三层记忆存储（Profile / Facts / Episodes），支持向量语义检索。

**替代方案**:
- 继续用 Redis：简单但不支持语义检索，全量返回不可扩展
- PostgreSQL + pgvector：成熟但引入重依赖
- Milvus：已有但过重，记忆数据量不需要分布式向量库

**理由**: LanceDB 嵌入式部署零运维，原生支持向量检索 + 元数据过滤，适合 per-user 记忆场景。三层结构（Profile 用户画像 / Facts 事实 / Episodes 对话片段）覆盖不同时间尺度的记忆需求。

### D4: Session Store — SQLite 替换内存

**选择**: 用 SQLite 持久化会话状态，替换当前内存 `_session_histories`。

**替代方案**:
- Redis：适合分布式但会话数据结构复杂，序列化开销大
- PostgreSQL：过重
- 保持内存：重启丢失，不可接受

**理由**: SQLite 零部署、事务安全、单机性能足够。会话数据天然是单用户访问模式，不需要分布式。未来如需水平扩展，可迁移到 PostgreSQL。

### D5: 前端技术栈 — React 18 + TypeScript + Vite

**选择**: React 18 + TypeScript + Vite + Zustand（状态管理）+ ECharts（图表）+ xterm.js（终端）。

**替代方案**:
- Vue 3 + Pinia：团队有经验但 React 生态更丰富，AI 相关组件库更多
- Next.js：SSR 不需要，增加复杂度

**理由**: React 生态中 AI Chat UI 组件（如 vercel/ai）成熟度高，TypeScript 保障大型项目可维护性，Vite 构建速度快。

### D6: 多通道通信 — SSE 主通道 + WebSocket 辅助

**选择**: SSE 作为 Agent 输出的主通道（单向流），WebSocket 用于需要双向交互的场景（如 ask_clarification）。

**替代方案**:
- 纯 WebSocket：双向但实现复杂，断线重连需要自己处理
- 纯 SSE：简单但不支持客户端主动推送
- gRPC Streaming：性能好但浏览器支持差

**理由**: Agent 输出天然是单向流，SSE 原生支持断点续传（Last-Event-ID）。少量双向交互场景用 WebSocket 补充。两者共享 Redis Streams 后端。

### D7: 工具生态 — Skill + MCP 双轨

**选择**: 自有 Skill 系统（SKILL.md 声明式）+ MCP 标准协议（开放生态），通过 CapabilityRegistry 统一管理。

**替代方案**:
- 纯 MCP：标准化但 Skill 的三阶段渐进加载、沙箱执行等高级能力 MCP 不支持
- 纯 Skill：封闭，无法接入外部工具生态

**理由**: Skill 提供深度集成能力（脚本执行、沙箱隔离），MCP 提供广度（接入 Cursor/Claude Desktop 等外部工具）。DeferredToolRegistry 渐进式加载避免 prompt 膨胀。

### D8: 监控体系 — Langfuse + ARMS + Prometheus 三层

**选择**:
- Langfuse：LLM 交互级监控（token/latency/cost/trace）
- ARMS：应用级监控（链路追踪/异常告警）
- Prometheus + Grafana：基础设施级监控（指标/看板）

**替代方案**:
- 纯 Langfuse：LLM 监控好但应用级能力弱
- 纯 OpenTelemetry：通用但 LLM 特化能力不足

**理由**: 三层各司其职，Langfuse 专注 AI 可观测性（prompt 版本、模型对比），ARMS 覆盖业务链路，Prometheus 兜底基础指标。

### D9: 测试策略 — 金字塔 + Evaluation

**选择**: 传统测试金字塔（单元 → 集成 → E2E）+ Agent Evaluation 系统（准确率/工具调用合理性/响应质量）。

**理由**: Agent 系统的非确定性输出无法用传统断言覆盖，需要 Evaluation 系统做统计级质量保障。传统测试覆盖确定性路径（API contract、Worker 逻辑、权限校验）。

### D10: 部署架构 — 单体优先，模块化拆分预留

**选择**: Phase 1-2 单体 FastAPI 部署，模块间通过接口隔离，Phase 3 按需拆分微服务。

**替代方案**:
- 一开始就微服务：过早优化，团队规模不支撑
- 永远单体：后期扩展困难

**理由**: 8-10 人团队单体开发效率最高，模块化设计（每个支柱独立目录、接口隔离）保证未来可拆分。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| K8s 沙箱冷启动延迟 > 5s | 用户体验差 | Warm Pool 预热 + 沙箱复用 + 分级策略（简单任务用 Native Worker） |
| LanceDB 单机性能瓶颈 | 高并发下记忆检索变慢 | 200ms 超时降级 + 异步预加载 + 未来可迁移 Milvus |
| PydanticAI 版本升级 breaking change | 核心引擎不可用 | 锁定版本 + Middleware 层隔离 + 适配器模式 |
| 多模型适配兼容性 | 不同模型 tool calling 行为不一致 | LiteLLM 统一适配 + per-model 测试用例 + 降级策略 |
| 前后端并行开发接口不稳定 | 联调成本高 | API contract 测试 + Mock Server + OpenAPI Schema 先行 |
| Agent Evaluation 标准难定义 | 质量无法量化 | 先建立基线 + 人工标注 + 渐进式自动化 |
| 团队并行开发冲突 | 代码冲突频繁 | 模块化目录隔离 + 接口先行 + 每日集成 |
| 三方服务（E2B/Langfuse）不可用 | 功能降级 | 每个外部依赖都有本地降级方案（E2B→Docker, Langfuse→本地日志） |

## Migration Plan

### Phase 1（4周）— 核心引擎上线
1. Agent Runtime + Middleware Pipeline
2. Sandbox Docker 模式 + 基础网络策略
3. Memory LanceDB 三层存储
4. Skill Engine + MCP Client
5. LLM Provider 多模型适配
6. FileSystem + Upload
7. Server 基础（FastAPI + WS + SQLite Session + Auth）
8. CLI 基础版
9. Prompt 模板体系
10. 测试框架 + 核心用例
11. Web 框架搭建 + 基础对话页面

### Phase 2（4周）— 产品形态完整
1. Web Client 完整功能（对话/Streaming/Artifact/Agent Hub）
2. Planning + SubAgent 完整实现
3. ACP 对接 + IM 通道
4. Server 扩展（ACP Bridge/计费/Checkpoint）
5. MCP Server
6. 多用户权限完善
7. Sandbox K8s 模式 + Warm Pool
8. 全链路测试 + Evaluation 系统

### Phase 3（4-6周）— 生态与稳定
1. Skill 市场
2. 性能优化（沙箱冷启动/LLM 延迟/内存）
3. 监控告警完善
4. IM 扩展 + ACP 优化
5. 安全加固（注入防护/审计/渗透测试）
6. 回归自动化 + Evaluation 持续迭代
7. 文档 + 产品运营

### Rollback 策略
- 每个 Phase 结束有可部署的里程碑版本
- 数据库 migration 支持回滚
- Feature flag 控制新功能灰度
- 沙箱引擎支持 Docker/K8s/E2B 三模式切换

## Open Questions

1. **Embedding 模型选型**：LanceDB 语义检索需要 Embedding 模型，用云端 API（OpenAI/阿里）还是本地部署（BGE/M3E）？影响延迟和成本。
2. **K8s 集群规格**：沙箱节点池需要多少资源？需要 GPU 节点吗？
3. **多租户隔离级别**：namespace 级别隔离还是集群级别？影响安全和运维复杂度。
4. **ACP 协议版本**：OpenClaw 当前支持哪个版本的 ACP？是否有 breaking change 计划？
5. **前端设计规范**：是否有现成的设计系统/组件库？还是从零搭建？
6. **合规要求**：数据存储是否有地域限制？审计日志保留期限？