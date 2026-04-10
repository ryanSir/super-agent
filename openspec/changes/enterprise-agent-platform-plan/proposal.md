## Why

当前智能体平台仅完成了主流程 POC 验证（ReasoningEngine → AgentFactory → Workers 链路可跑通），距离企业级生产部署存在大量缺口：无沙箱安全隔离、无多用户权限体系、无全链路监控、无测试覆盖、无前端产品界面、无 Skill/MCP 生态。需要从零系统性构建一个完整的企业级智能体运行时平台，覆盖 Agent Runtime、安全沙箱、记忆系统、工具生态、产品界面、监控计费等全部能力，支撑内部上线 → Beta → 正式发布三阶段目标。

## Non-goals

- 不做通用 AI 平台（只聚焦 Agent 运行时，不做模型训练/微调）
- 不做自研 LLM（通过 LLM Provider 适配第三方模型）
- 不做移动端 App（Phase 1-3 只覆盖 Web + CLI + IM 通道）
- 不做 Skill 自动生成（Skill 由人工编写，平台只负责加载和执行）
- 不做多集群跨区域部署（单集群内完成所有能力）

## What Changes

### Agent Runtime 核心引擎
- Agent Factory 三阶段构建（resolve → assemble → create）+ 13-stage Middleware Pipeline
- Context Manager 动态上下文组装（模板加载 + 运行时注入 + 模式对齐）
- ReasoningEngine 推理引擎（五维度复杂度评估 + 模糊区间 LLM 兜底 + 模式升级）
- ask_clarification 澄清机制（CLARIFY → PLAN → ACT 三阶段）
- 四种执行模式完整实现（DIRECT / AUTO / PLAN_AND_EXECUTE / SUB_AGENT）

### Planning + SubAgent 协作
- 任务分解引擎（DAG 依赖建模 + 并行调度）
- SubAgent Executor（最多 3 并发，禁止嵌套）
- Agent Team 协调（预置 researcher/analyst/writer + 自定义 Agent 注册）
- TodoToolset 任务追踪 + SummarizationProcessor 上下文压缩

### Sandbox 安全沙箱
- Docker + K8s 双模式沙箱引擎
- 4 种网络策略（NONE / ALLOWLIST / PROXY / FULL）
- AST 代码验证 + SSRF 防护 + Proxy 代理
- Warm Pool 预热池（冷启动优化）
- 沙箱自愈机制（OOM/超时自动回收重建）
- Pi Agent 实时日志 + JSONL IPC

### Memory 记忆系统
- LanceDB 三层存储（Profile / Facts / Episodes）替换当前 Redis 方案
- 语义召回（Embedding 向量检索 + 相关性排序）
- 自动提取 + 去重 + 时间衰减
- autoDream 定期整合（碎片记忆 → 结构化摘要）
- 多用户隔离（per-user namespace）

### Skill Engine 技能引擎
- SKILL.md frontmatter 加载 + 解析 + 校验
- 触发匹配（关键词 + 语义 + 显式调用三通道）
- 三阶段渐进加载（摘要注入 → 完整文档 → 脚本执行）
- Skill 市场（发布 / 发现 / 版本管理）

### MCP 工具生态
- MCP Client（stdio / SSE 双协议连接）
- 工具聚合 + 自动发现 + Schema 缓存
- MCP Server（Expose tools to Cursor / Claude Desktop）
- DeferredToolRegistry 渐进式加载

### LLM Provider 多模型适配
- 多提供商管理（Anthropic / OpenAI / Ollama / 国产模型）
- Streaming 流式输出 + Token 计数
- 自动降级 + 重试 + 熔断
- 模型路由（planning / execution / fast 三档）

### FileSystem 文件系统
- Read / Write / Edit / Glob / Grep 五大操作
- Permission ACL（per-user 读写权限控制）
- 虚拟路径映射（workspace 隔离）
- File Watching（变更监听 + 增量同步）

### Upload 文件上传
- markitdown 管线（PDF / Excel / Word / PPT → Markdown）
- 大文件分片上传 + 进度追踪
- 文件类型校验 + 安全扫描

### Server 服务层
- FastAPI + WebSocket 双通道
- Session Store（SQLite 持久化，替换内存方案）
- 基础 Auth（JWT + API Key）
- 计费 Checkpoint（per-request token 计量）
- ACP Bridge endpoint（跨通道 Session 接续）

### Streaming 事件流
- SSE 主通道（支持断点续传 + Last-Event-ID）
- WebSocket 双向通信（实时交互场景）
- Redis Streams 后端 + 事件协议标准化
- Heartbeat + 自动重连

### Security 安全体系
- 工具级权限模型（allow / deny / ask 三态）
- Prompt 注入检测（规则 + LLM 双层防护）
- 审计日志（全链路工具调用追踪）
- 沙箱安全策略（网络 / 文件 / 进程隔离）
- SQL 白名单（SELECT only）
- 临时 JWT Token 管理

### Monitoring 全链路监控
- Langfuse 模型交互监控（token / latency / cost）
- ARMS 应用监控（链路追踪 + 异常告警）
- Prometheus 指标导出 → Grafana 看板
- Pipeline 事件（步骤计时 + 元数据）
- 结构化日志（trace_id / session_id / request_id）

### Billing 计费系统
- Per-request / session / user 三级用量追踪
- 配额管理（限额 + 告警 + 熔断）
- 用量报告（日 / 周 / 月汇总）

### Web Client 前端
- React 18 + TypeScript + Vite + Pinia 项目搭建
- 对话界面 + Streaming 渲染 + Markdown 支持
- Artifact 展示（代码 / 图表 / 文件）
- A2UI Server-Driven UI 渲染引擎
- Agent Hub（Agent 列表 / 配置面板 / 模型选择）
- Skill 渲染组件
- xterm 终端集成

### CLI 命令行
- Textual TUI 交互界面
- in-process 模式（嵌入式调用）
- --json 结构化输出
- 会话管理（resume / history）

### ACP 对接
- messaging / notification / session / cron / webhook 5 个能力
- OpenClaw 双向通信
- IM 通道集成（钉钉 / 飞书 / 企业微信）

### Testing 测试体系
- pytest 框架搭建 + CI 集成
- Runtime 核心路径单元测试
- Sandbox 隔离验证测试
- API contract 测试
- 全链路集成测试
- Agent Evaluation 系统（准确率 / 工具调用合理性 / 响应质量）
- 性能基准测试

## Capabilities

### New Capabilities
- `agent-runtime`: Agent Factory 三阶段构建、13-stage Middleware Pipeline、Context Manager、ask_clarification、四种执行模式
- `planning-subagent`: 任务分解 DAG、SubAgent Executor、Agent Team 协调、TodoToolset
- `sandbox-engine`: Docker+K8s 双模式、网络策略、AST 验证、Warm Pool、自愈、Pi Agent
- `memory-system`: LanceDB 三层存储、语义召回、自动提取去重衰减、autoDream
- `skill-engine`: SKILL.md 加载解析、触发匹配、三阶段渐进加载、Skill 市场
- `mcp-hub`: MCP Client(stdio/SSE)、工具聚合自动发现、MCP Server、DeferredToolRegistry
- `llm-provider`: 多模型适配、Streaming、降级重试熔断、模型路由
- `filesystem-ops`: R/W/Edit/Glob/Grep、Permission ACL、虚拟路径、File Watching
- `upload-pipeline`: markitdown 转换管线、分片上传、安全扫描
- `server-layer`: FastAPI+WS、Session Store(SQLite)、Auth(JWT)、计费 Checkpoint、ACP Bridge
- `security-system`: 权限模型、注入检测、审计日志、沙箱策略、SQL 白名单
- `monitoring-observability`: Langfuse、ARMS、Prometheus+Grafana、Pipeline 事件、结构化日志
- `billing-system`: 三级用量追踪、配额管理、用量报告
- `web-client`: React 对话界面、Streaming 渲染、Artifact 展示、A2UI 引擎、Agent Hub
- `cli-client`: Textual TUI、in-process 模式、--json 输出
- `acp-integration`: 5 能力对接、OpenClaw 通信、IM 通道
- `testing-evaluation`: pytest 框架、单元/集成/安全/性能测试、Evaluation 系统

### Modified Capabilities
- `orchestrator`: ReasoningEngine 推理引擎需要从 POC 级别重构为生产级，增加完整的错误处理、监控埋点、配置外部化
- `workers`: Worker 层需要增加健康检查、重试机制、指标上报，WebSearchWorker 需要支持多搜索引擎
- `streaming`: SSE 端点需要增加 WebSocket 双向通道、事件协议标准化、断点续传完善
- `skills`: Skill 注册表需要增加版本管理、市场发布、社区发现能力
- `a2ui-protocol`: A2UI 需要增加更多组件类型、交互事件回传、组件注册机制完善

## Impact

- 代码目录：`src_deepagent/` 全部模块重构或新建，预计 20+ 子模块、200+ 文件、30000+ 行代码
- 前端目录：新建 React 项目，预计 50+ 组件、100+ 文件
- 基础设施依赖：Redis、Milvus/LanceDB、SQLite、Docker/K8s、E2B、Langfuse、Prometheus+Grafana
- API 变更：REST API 全面扩展（Agent CRUD、Session 管理、Skill 市场、计费查询等），WebSocket 新增
- 部署变更：需要 K8s 集群、沙箱节点池、监控栈、CI/CD Pipeline
- 团队影响：预计需要 8-10 人全职投入，分三个 Phase 共约 12-14 周完成