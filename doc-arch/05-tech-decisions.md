# 技术选型与决策记录

## ADR-001：Agent 框架选型

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳 |
| 背景 | 需要一个支持工具调用、流式输出、Sub-Agent 委派、结构化输出的 Python Agent 框架 |
| 候选方案 | LangChain / LangGraph、CrewAI、pydantic-ai + pydantic-deep、AutoGen |
| 决策 | **pydantic-ai（核心）+ pydantic-deep（Sub-Agent 扩展）** |
| 理由 | pydantic-ai 类型安全、原生 async、与 Pydantic v2 深度集成；pydantic-deep 提供 task() 委派和 Skill 三阶段加载，无需引入 LangChain 的重量级抽象 |
| 权衡 | pydantic-deep 是小众库（v0.3.3），社区支持有限；LangGraph 生态更成熟但引入了 Graph 状态机复杂度 |

---

## ADR-002：多模型路由策略

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳 |
| 背景 | 需要同时支持 Claude（Anthropic 原生）和 GPT/Qwen/DeepSeek/Gemini（OpenAI 兼容），且各模型推理格式不同（thinking tags / reasoning_content / anthropic_thinking） |
| 候选方案 | 全部走 LiteLLM 统一代理、Anthropic 原生 + OpenAI 兼容双路、全部走 OpenAI 兼容 |
| 决策 | **Anthropic 原生 SDK + OpenAI 兼容双路，通过 models.yaml 配置路由** |
| 理由 | Claude 走原生 SDK 可获得 extended thinking、流式 thinking blocks 等原生特性；其他模型走 OpenAI 兼容接口统一处理；YAML 配置解耦模型与代码 |
| 权衡 | 维护两套 Provider 适配器；LiteLLM 可统一但会丢失 Anthropic 原生特性 |

---

## ADR-003：沙箱执行引擎

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳（本地模式），E2B Cloud 待接入 |
| 背景 | 需要隔离执行用户代码，防止主进程污染；同时支持开发阶段快速迭代 |
| 候选方案 | E2B Cloud（托管沙箱）、Docker 本地容器、本地子进程、Firecracker microVM |
| 决策 | **E2B SDK + 本地子进程双模式，通过 E2B_USE_LOCAL 切换** |
| 理由 | 开发阶段用本地子进程（零依赖、快速启动）；生产用 E2B Cloud（强隔离、网络隔离）；同一套 SandboxWorker 接口，切换无感 |
| 权衡 | 本地模式无真正隔离，仅适合开发；E2B Cloud 有冷启动延迟（~2s） |

---

## ADR-004：事件流传输协议

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳 |
| 背景 | Agent 执行过程需要实时向前端推送 thinking / tool_call / text_stream 等多种事件，支持断点续传 |
| 候选方案 | WebSocket 双向流、SSE 单向推送、HTTP 长轮询、gRPC 流 |
| 决策 | **SSE（主）+ WebSocket（备用）** |
| 理由 | SSE 天然支持 Last-Event-ID 断点续传，浏览器原生支持，无需额外握手；Redis Streams 作为中间缓冲，解耦生产者（Agent）和消费者（SSE 端点） |
| 权衡 | SSE 单向，不支持客户端推送；WebSocket 保留为双向通道备用 |

---

## ADR-005：状态存储选型

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳 |
| 背景 | 需要存储会话状态、事件流缓冲、用户记忆（Profile + Facts），要求低延迟、支持 TTL |
| 候选方案 | Redis、PostgreSQL、MongoDB、内存（进程内） |
| 决策 | **Redis（Streams + Hash）** |
| 理由 | Redis Streams 天然适合事件流缓冲和断点续传；Hash 适合会话状态和记忆存储；200ms 超时降级保证记忆系统不阻塞主流程 |
| 权衡 | 纯内存存储，重启丢失（需配置 AOF/RDB 持久化）；不适合复杂查询 |

---

## ADR-006：前端渲染架构

| 项目 | 内容 |
|------|------|
| 状态 | 已采纳 |
| 背景 | Agent 输出多样（文本、代码、图表、终端、Sub-Agent 状态），需要动态渲染不同组件 |
| 候选方案 | 纯 Markdown 渲染、固定组件列表、A2UI 动态组件注册表 |
| 决策 | **A2UI 协议：后端发送 render_widget 事件，前端 ComponentRegistry 动态分发** |
| 理由 | 后端通过事件类型控制前端渲染，新增组件类型无需修改核心渲染逻辑；ComponentRegistry 统一管理组件映射 |
| 权衡 | 前后端需维护一致的事件类型枚举；组件类型爆炸时需要治理 |

---

## 架构约束

| 约束 | 说明 |
|------|------|
| 异步优先 | 所有 I/O 操作必须使用 async/await，禁止阻塞主线程 |
| 配置外置 | 所有配置通过 Pydantic BaseSettings + .env，禁止硬编码 |
| 工具渐进加载 | 工具注入遵循摘要→详情→执行三阶段，不全量注入 Prompt |
| 沙箱隔离 | 用户代码执行必须在沙箱内，禁止直接在主进程执行 |
| 记忆降级 | 记忆检索超时（200ms）时静默降级，不阻塞主流程 |
| 不依赖 LangChain | Agent 框架统一使用 pydantic-ai + pydantic-deep |
