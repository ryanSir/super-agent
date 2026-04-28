# Agent 框架六方对比：Hermes vs DeerFlow vs Pydantic-Deep vs Super-Agent vs AgentScope vs Deep Agents

> 架构设计、核心流程、工具系统、沙箱执行、企业落地全方位对比
>
> Agent Framework Comparison v2.0 | 2026-04-16

---

## 1. 项目概览

| | Hermes Agent | DeerFlow 2.0 | Pydantic-Deep | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 出品方 | Nous Research | 开源社区（字节跳动发起） | 社区 | 内部项目 | 阿里巴巴（SysML+蚂蚁集团） | LangChain 官方 |
| 定位 | 多平台智能助手 + Gateway消息网关 | LangGraph超级Agent + Web研究平台 | Claude Code风格编码Agent框架 + CLI | 企业级混合AI Agent引擎，Python控制面 + 沙箱自主执行 | 多Agent协作平台 + 分布式运行时 | 通用Agent SDK + CLI，"inspired by Claude Code" |
| 核心 | 自研编排循环，原生多平台，无框架依赖 | LangGraph StateGraph，中间件链，配置驱动 | pydantic-ai Agent，类型安全，工厂模式 | pydantic-deep编排 + 五维度复杂度路由 + E2B沙箱 | ReActAgent + Pipeline/MsgHub消息传递 | LangGraph + 洋葱模型中间件栈 |
| 特色 | 10+平台Gateway，MCP集成，完全透明控制 | Web UI，LangSmith追踪，沙箱执行 | 结构化配置，Hooks，E2B协作 | 四种执行模式自动路由，Redis全链路状态，渐进式工具加载 | 多Agent编排原语丰富，A2A协议，阿里生态 | 中间件可组合，BackendProtocol沙箱抽象，agentskills.io规范 |
| 架构 | 单Agent + 工具注册器 + 自循环 | LangGraph + Middleware + FastAPI + Nginx | pydantic-ai + ToolsetBE + Backend组合 | FastAPI + pydantic-deep + ReasoningEngine + Redis Stream | AgentBase + Pipeline + MsgHub + Toolkit | LangGraph + Middleware Stack + BackendProtocol |
| 框架依赖 | 零框架（自研） | LangGraph + LangChain | pydantic-ai | pydantic-deep（可降级到原生pydantic-ai） | 自研框架（依赖标准LLM SDK） | LangGraph + LangChain（核心依赖） |
| GitHub Star | ~15k | ~10k | ~5k | — | ~23.8k | ~20.9k |
| 协议 | MIT | MIT | MIT | 私有 | Apache 2.0 | MIT |

---

## 2. 架构分层对比

### 2.1 入口层

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | CLI + Gateway(10+平台) | Web UI + FastAPI + LangGraph Server | CLI(Typer) + Python API | REST API + WebSocket + SSE流式 | Python SDK + AgentScope Studio(Web) + A2A协议 | CLI(Textual TUI) + ACP编辑器插件 + SDK |
| 细节 | Telegram/Discord/Slack/WhatsApp/Email 基本覆盖所有IM | Next.js前端 + Nginx代理 + SSE流式 | chat/run命令 + create_deep_agent()工厂 | POST /api/agent/query + GET /stream/{session_id} 断点续传 | agentscope.init()初始化，Studio提供Web监控和输入，A2A跨服务Agent通信 | pip install deepagents 即用，Zed编辑器ACP集成，create_deep_agent()返回LangGraph Runnable |
| 内置HTTP API | 有（Gateway） | 有 | 无 | 有 | 无（SDK-first） | 无（SDK-first） |
| 优势 | 最广的平台覆盖 | 最完整的Web体验 | 最灵活的编程接口 | 面向企业集成，API-first | A2A跨服务通信 | 嵌入性最强，SDK-first |

### 2.2 Agent编排

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | 自研while循环 | LangGraph StateGraph | pydantic-ai Agent.run() | ReasoningEngine五维度→四模式 | Pipeline + MsgHub + ChatRoom | LangGraph标准agent loop + 中间件栈 |
| 编排原语 | 单循环(iterative/parallel/pipeline) | 图(state/node/edge) | 单Agent循环 | DIRECT/AUTO/PLAN_AND_EXECUTE/SUB_AGENT | SequentialPipeline, FanoutPipeline, MsgHub广播, PlanNotebook任务分解 | write_todos自组织 + task()委派，无显式模式路由 |
| 多Agent | depin_task委派 | SubagentExecutor | SubAgent角色 | task()工具委派 | MsgHub群组通信 + FanoutPipeline并行 + A2AAgent远程委派 | SubAgentMiddleware隔离上下文，支持并行task() |
| 亮点 | 零依赖完全控制 | 图约束状态管理 | 类型安全 | 规则优先避免LLM浪费，简单任务秒级响应 | 编排原语最丰富，MsgHub自动广播 | 中间件可组合性最强 |

### 2.3 LLM集成

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | 3种API直连 | LangChain ChatModel | pydantic-ai Model标识符 | 双通道(Claude原生+OpenAI兼容) | ChatModelBase + 专用Wrapper(6家) + Formatter系统 | provider:model字符串解析 + LangChain init_chat_model() |
| 支持厂商 | OpenAI/Anthropic/Codex | LangChain生态全覆盖 | OpenAI/Anthropic等 | Claude + OpenAI兼容 | OpenAI, Anthropic, DashScope(通义), Gemini, Ollama, DeepSeek, Trinity | Anthropic(默认), OpenAI, Google, Ollama, OpenRouter |
| 特色 | 零中间层 | 统一Thinking | 自动启用Thinking | 按角色分配模型控成本（编排用强模型，执行用快模型） | Formatter按厂商格式化，流式JSON修复，阿里系原生支持 | Anthropic prompt caching自动应用，per-provider profiles |

### 2.4 工具系统

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | ToolRegistry中央注册 | LangChain BaseTool + 配置驱动 | FunctionTool装饰器 | 三层(Workers→Tools→Agent) + MCP Toolsets | Toolkit类(~2000行) + 中间件 + 工具分组 | BackendProtocol工具 + 中间件注入 |
| 注册 | register()+dispatch() | use字段配置 | @tool装饰器 | 按职责分组，按模式黑名单过滤 | register_tool_function() + 动态JSON Schema | 内置工具(read/write/edit_file, ls, glob, grep, execute) |
| 工具分组 | 无 | 无 | ToolsetConfig | native/sandbox/ui/memory/plan | create_tool_group()元工具，Agent可动态管理工具集 | 无显式分组，中间件控制工具可见性 |
| 中间件 | 无 | 中间件链 | Hooks | Hooks | 洋葱模型中间件包装call_tool_function | 洋葱模型中间件栈（最完整） |
| 后台执行 | 无 | 无 | 无 | 无 | 有（view_task/cancel_task/wait_task） | 无 |
| MCP | 完整(含Sampling) | stdio/SSE/HTTP | 无 | 多端点+DefaultArgsToolset凭证注入+FastMCPToolset | StdIO有状态 + HTTP无状态/有状态 三种客户端 | langchain-mcp-adapters |

### 2.5 沙箱执行

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | 6种隧道：PTY/Docker/SSH/Daytona/Modal/Sing. | LocalSandbox / AioSandbox(Docker) | Backend路由：State/Local/Docker/Composite | E2B双模式 + Pi Agent自主执行 | 无内置沙箱 | BackendProtocol：State/Filesystem/LocalShell/Composite + 合作伙伴(Daytona/Modal/QuickJS/Runloop) |
| 隔离级别 | 多种可选 | 进程级 | 组合策略 | 容器级(E2B) + JWT防密钥泄露 | 宿主进程内执行，依赖K8s容器隔离 | State(内存,最安全) / LocalShell(shell=True,需显式opt-in) |
| 亮点 | 隧道种类最多 | 简单直接 | 组合灵活 | 沙箱内有独立Agent（Pi Agent），不只执行代码 | 短板，需自建 | BackendProtocol抽象最干净，同一代码零改动切换环境 |

### 2.6 子代理/委派

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | depin_task：深度2，3并发 | SubagentExecutor：3并发，15min超时 | 3角色(researcher/analyst/writer) + 自定义 | task()扁平委派，3预置角色 + 自定义注册 | MsgHub + FanoutPipeline + A2AAgent + AgentSkill | SubAgentMiddleware，隔离上下文 |
| 通信模型 | 上下文完全隔离 | LangGraph状态 | 指令区分角色 | 共享MCP/Skills，扁平层级 | Msg消息传递，observe()观察 + reply()回复 | 隔离上下文，中间步骤对父Agent不可见 |
| 远程委派 | 无 | 无 | 无 | 无 | A2A协议跨服务（支持Nacos服务发现） | ACP协议（编辑器集成） |
| 亮点 | 支持递归委派 | 框架级编排 | 简单可控 | 扁平避免递归爆炸 | 多Agent通信模型最成熟 | 子代理可配自定义模型/工具/中间件/结构化输出 |

### 2.7 记忆系统

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | MemoryManager + 外部提供者 | FileMemoryStorage + LLM摘要 | MEMORY.md文件 + Checkpoint | Redis持久化（Profile + Facts），200ms超时降级 | 双层：WorkingMemory + LongTermMemory | AGENTS.md文件，多层加载(base→user→project→team) |
| 工作记忆 | 内存级 | JSON文件 | 文件级 | Redis Hash | InMemory / Redis / SQLAlchemy / Tablestore 四种后端 | 文件级 |
| 长期记忆 | Horizon外部API | LLM摘要压缩 | 无 | Facts列表 | Mem0集成 + ReMe(阿里自研，跨用户/跨Agent记忆共享) | 无（Agent通过edit_file自更新AGENTS.md） |
| 压缩 | 无 | LLM摘要 | 无 | 无 | ReActAgent内置CompressionConfig，token阈值触发 | SummarizationMiddleware自动压缩 |
| 亮点 | 外部可扩展 | 智能压缩 | 简单可靠 | 生产级：Redis分布式、超时降级、锁保护 | 后端最多，双层最完整，ReMe跨Agent共享 | 遵循agents.md开放规范，多层覆盖 |

### 2.8 上下文管理

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 方式 | ContextCompressor三阶段压缩 | Summarization中间件 | ContextManager/Middleware + Eviction | 12段模板动态组装 + 框架自动压缩 | Formatter系统 + TruncatedFormatter + 记忆压缩 | SummarizationMiddleware(自动) + compact_conversation工具(手动) |
| Token计数 | 无专用 | LangChain内置 | 框架内置 | 框架内置 | 5种专用TokenCounter(OpenAI/Anthropic/Gemini/HuggingFace/Char) | 模型感知默认值，从chat model profiles计算 |
| 亮点 | 压缩策略最精细 | 框架自动恢复 | 自适应 | 模板化按模式裁剪，避免Prompt膨胀 | Token计数最精确 | 自动+手动双模式，溢出时优雅降级

---

## 3. 功能矩阵对比

| 功能维度 | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents | 最佳选择 |
|---|---|---|---|---|---|---|---|
| 多平台消息网关 | 10+平台原生 | 无 | 无 | 无 | 无 | 无 | Hermes |
| Web UI/监控 | 无 | Next.js+SSE | DeepResearch Web | React A2UI+SSE断点续传 | AgentScope Studio | 无(CLI+编辑器) | DeerFlow(体验) / AS(监控) |
| 作为库嵌入 | 困难 | DeepFlowClient | create_deep_agent() | create_deep_agent() | agentscope.init() | create_deep_agent() | Deep Agents / PD |
| 多Agent编排 | 单Agent+委派 | SubagentExecutor | SubAgent角色 | task()委派 | Pipeline+MsgHub+A2A | SubAgentMiddleware | AgentScope |
| 中间件架构 | 无 | 中间件链 | Hooks | Hooks | Toolkit中间件 | 洋葱模型中间件栈 | Deep Agents |
| 类型安全/结构化输出 | JSON字符串 | LangChain类型 | Pydantic Model | Pydantic v2全链路(Enum状态机) | Msg ContentBlock + Pydantic | Pydantic+TypedDict+dataclass | Super-Agent |
| 成本追踪/预算控制 | Token计数 | LangSmith追踪 | USD预算强制执行 | 框架级token追踪+计费预留 | 无内置 | LangSmith | PD |
| MCP协议支持 | 完整(含Sampling) | stdio/SSE/HTTP | 无原生MCP | 多端点+凭证注入+自动刷新 | StdIO+HTTP(有状态/无状态) | langchain-mcp-adapters | Hermes(协议全) / SA(企业集成) |
| Skills技能系统 | 渐进加载+自改进 | SKILL.md+演化 | Skill路由+载本 | 三阶段渐进加载+双执行模式 | AgentSkill+ToolGroup元工具 | agentskills.io开放规范 | SA(加载策略) / DA(规范化) |
| 沙箱执行 | 6种隧道 | Docker | Backend路由 | E2B+Pi Agent自主执行 | 无 | BackendProtocol(5种+合作伙伴) | SA(自主Agent) / DA(抽象最干净) |
| 可观测性/追踪 | JSONL日志 | LangSmith+Langfuse | 成本回调 | Langfuse+OTel+结构化日志 | OTel原生+Studio+10种Hook | LangSmith(核心依赖) | DeerFlow / AgentScope |
| 执行模式路由 | 无 | 无 | 无 | 四模式自动路由(DIRECT/AUTO/PLAN/SUB_AGENT) | 无 | 无 | Super-Agent(独有) |
| 分布式状态管理 | 无 | LangGraph检查点 | Checkpoint文件 | Redis Hash+Stream+分布式锁 | Redis/SQLAlchemy/Tablestore Session | LangSmithBackend | Super-Agent / AgentScope |
| 远程Agent通信 | 无 | 无 | 无 | 无 | A2A协议+Nacos服务发现 | ACP(编辑器) | AgentScope |
| 记忆系统深度 | 外部API | 文件+LLM摘要 | 文件级 | Redis Profile+Facts | 双层+4后端+ReMe跨Agent共享 | AGENTS.md文件 | AgentScope |
| 安全威胁模型 | 无 | 无 | 无 | JWT+凭证隔离 | 无 | 正式文档(9项威胁分析) | Deep Agents(文档) / SA(实现) |
| 框架依赖/锁定 | 零(自研) | 高(LangChain) | 中(pydantic-ai) | 中(可降级) | 中高(全套自研) | 高(LangChain核心依赖) | Hermes(零依赖) |

---

## 4. 核心数据流对比

### 4.1 Hermes Agent 数据流

```
用户输入 → CLI / Gateway(10+平台)
  → AiAgent 创建 → PromptBuilder 构建系统提示词
  → WHILE LOOP（消息准备 → LLM调用 → 解析判断 → 工具执行）
  → 结束 → Session持久化 → 记忆同步 → 批量回复
```

### 4.2 DeerFlow 数据流

```
用户输入 → Nginx + FastAPI → LangGraph Server
  → 中间件链: ThreadData → Upload → Sandbox → Memory → ...
  → LANGGRAPH STATEGRAPH（状态初始化 → LLM + Set → 中间件检查 → 监控 → 分场执行）
  → SSE流式 → 检查点持久化 → 记忆融合
```

### 4.3 Pydantic-Deep 数据流

```
用户输入 → CLI / Python API → Agent.run(deep)
  → 动态指令: @agent.instructions + Deps注入
  → AGENTIC LOOP（历史处理 → LLM调用 → Toolset处理 → result → Backend执行）
  → Checkpoint → Memory更新 → 成本回报
```

### 4.4 Super-Agent 数据流

```
用户输入 → REST API Gateway
  → ReasoningEngine 五维度复杂度评估
    → 规则匹配（正则+关键词）→ 命中则直接路由
    → 未命中 → LLM分类器（gpt-4o-mini，15s超时）
  → 执行模式确定（DIRECT/AUTO/PLAN_AND_EXECUTE/SUB_AGENT）
  → AgentFactory 创建 pydantic-deep Agent
    → 12段模板动态组装 System Prompt
    → 按模式注入工具组 + MCP Toolsets + SkillsToolset
    → 注入记忆（200ms超时降级）
  → Agent.run(deep) 进入 Agentic Loop
    → LLM调用 → 工具执行 → Redis Stream事件推送 → SSE实时输出
    → 如需沙箱：SandboxWorker → E2B → Pi Agent自主执行 → JSONL解析
    → 如需委派：task() → SubAgent创建 → 独立执行 → 结果汇总
  → Session持久化 → Memory更新 → Langfuse上报
```

### 4.5 AgentScope 数据流

```
用户输入 → Python SDK / AgentScope Studio
  → agentscope.init() 初始化运行时
  → Agent创建（ReActAgent / 自定义AgentBase子类）
  → Pipeline编排（Sequential / Fanout / MsgHub）
    → Msg消息传递 → Formatter按厂商格式化 → LLM调用
    → Toolkit工具执行（中间件包装）→ 结果回传
    → MsgHub自动广播给其他参与者
  → WorkingMemory持久化 → LongTermMemory(ReMe)更新
  → OTel Span上报 → Studio可视化
```

### 4.6 Deep Agents 数据流

```
用户输入 → CLI(Textual TUI) / ACP(编辑器) / SDK
  → create_deep_agent() 组装中间件栈
    → SkillsMiddleware 注入技能摘要
    → MemoryMiddleware 加载 AGENTS.md
    → SubAgentMiddleware 注册 task() 工具
    → PermissionsMiddleware 文件权限（最后执行）
  → LangGraph Agent Loop
    → LLM调用 → 工具执行(通过BackendProtocol) → 结果回传
    → SummarizationMiddleware 自动压缩（超阈值时）
    → 如需委派：task() → 子Agent隔离执行 → 单一结果返回
  → LangSmith追踪上报
```

---

## 5. 硬性维度对比

### 5.1 社区 & 生态成熟度

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| GitHub Star | ~15k | ~10k | ~5k | — | ~23.8k | ~20.9k |
| 贡献者 | Nous Research团队 | 社区(字节发起) | 社区 | 内部团队 | 60人(阿里SysML+蚂蚁) | LangChain团队 |
| 版本迭代 | 活跃 | 活跃(2.0重构) | 中等 | 快速 | 28版本，v1.0后月均2个 | 94版本，8天3个release |
| 商业支持 | 无 | 无 | 无(Pydantic公司背书) | 内部 | 阿里巴巴+蚂蚁集团，EMNLP论文 | LangChain公司官方 |
| 生态 | Gateway插件 | LangChain生态 | pydantic-ai生态 | 内部 | ReMe+Spark Design+Alias产品 | LangSmith+合作伙伴沙箱(Daytona/Modal等) |

### 5.2 生产就绪度

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 生产案例 | 多个IM机器人 | Web研究平台 | 偏CLI工具 | 内部验证中 | 阿里云、蚂蚁集团、Alias产品 | pre-1.0(0.5.x)，API快速变化 |
| 错误恢复 | Session持久化 | LangGraph检查点 | Checkpoint文件 | Redis断点续传+200ms超时降级+Worker懒加载跳过不可用 | StateModule序列化/反序列化，max_iter自动摘要兜底 | 上下文溢出优雅降级，Backend错误归一化 |
| 人机协作 | 无 | 无 | 无 | 无 | handle_interrupt()实时中断+记忆保留 | human-in-the-loop审批 |
| 优雅降级 | 无明确机制 | 中间件可跳过 | Backend组合降级 | 记忆超时降级、Langfuse可选零开销、Worker不可用自动跳过、pydantic-deep不可用降级到原生pydantic-ai | 无明确机制 | StateBackend默认安全，上下文溢出fallback |

### 5.3 安全模型

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 注入防护 | 无 | 中间件可拦截 | 无 | security模块预留 | 无 | 威胁模型已识别但未防护（memory/skill文件无sanitization） |
| 权限隔离 | Gateway层 | 配置驱动use字段 | Hooks | JWT临时令牌(10min TTL) + DefaultArgsToolset凭证隔离 | 无内置，可用Toolkit中间件实现 | PermissionsMiddleware文件权限，StateBackend默认安全 |
| 审计能力 | JSONL日志 | LangSmith全链路 | 成本回调 | Langfuse+结构化日志(session_id/trace_id)+Redis Stream | OTel traces | LangSmith全链路 |
| 沙箱隔离 | 6种隧道 | Docker进程级 | Backend路由 | E2B容器级 + JWT防密钥泄露 | 无，依赖K8s | BackendProtocol分级(State最安全→LocalShell需opt-in) |
| 威胁模型文档 | 无 | 无 | 无 | 无 | 无 | 有（9项威胁分析） |

### 5.4 学习曲线 & 团队匹配

| | Hermes | DeerFlow | PD | Super-Agent | AgentScope | Deep Agents |
|---|---|---|---|---|---|---|
| 前置知识 | Python基础，需读懂自研逻辑 | LangChain+LangGraph+Next.js | pydantic-ai+Pydantic v2 | pydantic-ai+FastAPI+Redis | Python 3.10+，async/await | LangGraph+LangChain，Python 3 |
| 上手难度 | ⭐⭐⭐（自研逻辑需深入理解） | ⭐⭐⭐⭐（全栈技术栈要求高） | ⭐⭐（类型系统友好） | ⭐⭐⭐（概念多但分层清晰） | ⭐⭐⭐（API丰富，概念多） | ⭐⭐⭐（中间件概念需理解） |
| 适合团队 | 全栈独立开发者，需多平台覆盖 | 前后端全栈团队，需完整Web研究平台 | Python后端团队，重视类型安全 | 企业后端团队，有Redis/微服务经验 | 大型AI团队，需多Agent协作+分布式 | SDK优先团队，重视可组合性+编辑器集成 |
| 文档质量 | 中等 | 良好 | 良好 | 内部文档 | 优