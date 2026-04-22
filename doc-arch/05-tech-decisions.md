# 技术选型与决策记录

本文档记录 Super Agent 核心技术选型的决策理由，采用 ADR（Architecture Decision Record）风格。

---

## ADR-001: Agent 框架选择 PydanticAI + pydantic-deep

**状态**: 已采纳

**背景**: 需要一个支持多 Agent 协作、工具调用、流式输出的 Agent 框架。

**候选方案**:
- LangChain / LangGraph
- CrewAI
- AutoGen
- PydanticAI + pydantic-deep

**决策**: 选择 PydanticAI + pydantic-deep

**理由**:
- 类型安全：基于 Pydantic，输入输出有完整类型校验
- 轻量：不引入 LangChain 的重抽象层，减少调试黑盒
- Sub-Agent 原生支持：pydantic-deep 内置 task() 委派机制
- Extended Thinking：原生支持 Claude 的 extended thinking 能力
- Hook 系统：PRE/POST 工具调用钩子，便于注入监控和安全逻辑
- Context Manager：内置上下文窗口管理（200K token 限制）

**权衡**: 生态不如 LangChain 丰富，但项目需要的是精确控制而非生态广度。

---

## ADR-002: 沙箱执行选择 E2B

**状态**: 已采纳

**背景**: Agent 需要执行用户指定的代码（Python 脚本、数据处理等），必须隔离执行。

**候选方案**:
- Docker 容器
- AWS Lambda
- E2B (Tencent Cloud 版)
- 本地子进程

**决策**: E2B 作为生产方案，本地子进程作为开发方案，通过 `SANDBOX_PROVIDER` 环境变量切换。

**理由**:
- 完整隔离：E2B 提供独立容器，网络/文件/进程完全隔离
- 临时凭证：沙箱只拿到 10 分钟有效的 JWT，不接触真实 API Key
- Pi Agent 集成：沙箱内运行 Pi Coding Agent，支持自主 ReAct 循环
- 秒级启动：比冷启动 Docker 更快
- 双模式切换：开发时用本地子进程（零成本），生产用 E2B（安全隔离）

**权衡**: E2B 是第三方服务，有供应商锁定风险。通过 SandboxManager 抽象层缓解。

---

## ADR-003: 事件流选择 Redis Stream

**状态**: 已采纳

**背景**: 后端 Agent 执行过程中产生的事件（thinking、tool_call、text_stream 等）需要实时推送到前端。

**候选方案**:
- Kafka
- RabbitMQ
- Redis Stream
- 内存队列 (asyncio.Queue)

**决策**: Redis Stream

**理由**:
- 已有依赖：Redis 已用于会话管理和记忆存储，不引入新组件
- 轻量：不需要 Kafka 的分区/副本/ZooKeeper 复杂度
- 持久化：Stream 数据持久化，支持 Last-Event-ID 断点续传
- 游标消费：XREAD 支持阻塞读取 + 游标追踪，天然适配 SSE
- TTL 管理：通过 MAXLEN 和 TTL 自动清理过期事件

**权衡**: 单 Redis 实例有吞吐上限，但当前规模（单用户/少量并发）完全够用。

---

## ADR-004: 前端渲染选择 A2UI 协议

**状态**: 已采纳

**背景**: Agent 输出不仅是文本，还包括图表、终端、进度条等富组件，需要灵活的 UI 渲染方案。

**候选方案**:
- 前端硬编码组件映射
- Markdown + 自定义扩展
- A2UI（Agent-to-UI）后端驱动协议

**决策**: A2UI 协议 — 后端发送结构化 JSON，前端动态渲染组件。

**理由**:
- 后端控制：新增可视化类型不需要改前端代码，后端发 JSON 即可
- 类型安全：`render_widget` 事件携带 `ui_component` + `props`，前端按 schema 渲染
- 流式更新：通过 SSE 增量推送，支持实时更新图表数据
- 解耦：前端只需维护组件注册表（ComponentRegistry），不关心业务逻辑

**权衡**: 前端需要预注册所有组件类型，不支持完全动态的 UI。

---

## ADR-005: 工具加载选择渐进式策略

**状态**: 已采纳

**背景**: 系统有 10 个内置工具 + N 个 Skills + M 个 MCP 工具，全量注入 System Prompt 会导致 Token 膨胀。

**决策**: 三阶段渐进加载

**策略**:

| 阶段 | 时机 | 注入内容 | Token 成本 |
|------|------|----------|-----------|
| Stage 1 | 启动时 | 工具名称 + 一行描述 | 极低 |
| Stage 2 | Agent 主动搜索 | 完整文档 + 参数 schema | 中等 |
| Stage 3 | Agent 调用执行 | 实际执行 | 无额外 Token |

**理由**:
- Prompt 经济性：AI 在短上下文准确率远高于长上下文
- 按需加载：Agent 只在需要时获取工具详情
- Skills 和 MCP 统一策略：`search_skills()` 和 `tool_search()` 接口一致

**权衡**: Agent 需要额外一轮 LLM 调用来搜索工具详情，增加少量延迟。

---

## ADR-006: 复杂度评估选择规则 + LLM 混合方案

**状态**: 已采纳

**背景**: 需要根据用户查询自动选择执行模式（DIRECT/AUTO/PLAN_AND_EXECUTE/SUB_AGENT）。

**决策**: 三级分类 — 显式指定 → 规则匹配 → 复杂度评估（含 LLM 兜底）

**理由**:
- 零延迟优先：规则匹配（正则）无网络开销，覆盖 80% 场景
- 五维度评估：task_count / domain_span / dependency_depth / output_complexity / reasoning_depth，加权打分
- LLM 兜底：仅在模糊区间 [0.35, 0.55] 调用 fast_model，5s 超时降级
- 可升级：DIRECT 模式回答不足时可升级为 AUTO（最多一次）

**权衡**: 规则匹配依赖关键词，对新表述可能误判。LLM 兜底缓解此问题。

---

## 架构约束

| 约束 | 说明 |
|------|------|
| Python 3.12+ | 使用 type hint 新语法（`X | Y`）和 asyncio 改进 |
| 单进程部署 | 当前为单 FastAPI 进程，通过 asyncio 并发 |
| Redis 必需 | 会话管理和事件流依赖 Redis，但连接失败可降级运行 |
| LLM 必需 | 核心推理能力依赖外部 LLM Provider |
| 最多 3 个并发 Sub-Agent | `MAX_CONCURRENT_SUBAGENTS=3`，防止 Token 爆炸 |
