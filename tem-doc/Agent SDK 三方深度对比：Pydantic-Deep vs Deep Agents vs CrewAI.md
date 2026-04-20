# Agent SDK 三方深度对比：Pydantic-Deep vs Deep Agents vs CrewAI

> Agent SDK Comparison v1.0 | 2026-04-17
>
> 源码级分析 | 稳定性 & Bug 清单 | 维护成本评估 | 选型建议

---

## 0. 为什么是这三个

Agent 框架分两类：

**SDK 型**（pip install → create_agent() → 框架团队维护核心逻辑）
- ✅ Pydantic-Deep — `pip install pydantic-deep`
- ✅ Deep Agents — `pip install deepagents`
- ✅ CrewAI — `pip install crewai`

**应用型**（git clone → 自己跑整个应用 → 自己维护全部代码）
- ❌ DeerFlow — 28.6K 行自建代码，16 个自建中间件
- ❌ Hermes — 自研编排循环 + 10+ Gateway
- ⚠️ AgentScope — SDK 可用，但核心价值在平台能力

SDK 型的核心价值：框架团队帮你修 bug、加功能，你只需 `pip install -U`。

---

## 1. 项目概览

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 出品方 | 社区（Pydantic 公司背书） | LangChain 官方 | CrewAI Inc.（独立公司） |
| 定位 | Claude Code 风格编码 Agent 框架 | 通用 Agent SDK，"inspired by Claude Code" | 多 Agent 协作框架 + 工作流引擎 |
| 版本 | v0.3.3 | v0.5.3 | v1.14.1 |
| GitHub Star | ~16K（pydantic-ai） | ~21K | ~49K |
| 协议 | MIT | MIT | MIT |
| Python | >=3.12 | >=3.11 | >=3.10,<3.14 |
| 底层框架 | pydantic-ai | LangGraph + LangChain | 自研（零 LangChain 依赖） |
| 核心 API | `create_deep_agent()` | `create_deep_agent()` | `Crew(agents, tasks)` |
| 返回类型 | pydantic-ai Agent | LangGraph CompiledGraph | Crew 实例 |
| 代码规模 | ~8.4K 行 / 33 模块 | ~10K+ 行 | ~30K+ 行 |
| 迭代速度 | 中等 | 极快（8 天 3 个 release） | 快（v1.14.x） |
| 商业支持 | 无（Pydantic 公司间接背书） | LangChain 公司官方 | CrewAI Inc. + Enterprise SaaS |

---

## 2. 架构分层对比

### 2.1 编排模型（根本区别）

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 编排范式 | 单 Agent 自主循环 + task() 委派 | 单 Agent 自主循环 + task() 委派 | 显式多 Agent 流程编排 |
| 谁决定拆分 | LLM 自主判断 | LLM 自主判断 | 开发者预定义 |
| 流程控制 | Agent.run() 内部循环 | LangGraph agent loop | Process.sequential / hierarchical |
| 多 Agent | SubAgent 角色（researcher/analyst/writer） | SubAgentMiddleware 隔离上下文 | Crew(agents=[], tasks=[], process=) |
| 工作流 | 无 | 无 | Flow 系统（@start/@listen/@router 装饰器） |

代码对比：

```python
# Pydantic-Deep — LLM 自主决定
agent = create_deep_agent(subagents=[
    {"name": "researcher", "description": "..."},
])
result = await agent.run("写一份市场分析报告")
# Agent 自己决定是否调用 task("researcher", "调研竞品")

# Deep Agents — 几乎一样
agent = create_deep_agent(subagents=[...])
result = agent.invoke({"messages": [HumanMessage("写一份市场分析报告")]})

# CrewAI — 开发者定义流程
researcher = Agent(role="市场研究员", goal="...", tools=[search_tool])
writer = Agent(role="报告撰写者", goal="...", tools=[])
crew = Crew(
    agents=[researcher, writer],
    tasks=[
        Task(description="调研竞品", agent=researcher),
        Task(description="撰写报告", agent=writer),
    ],
    process=Process.sequential,
)
result = crew.kickoff()
```

### 2.2 底层框架依赖

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 核心依赖 | pydantic-ai（1 个） | langchain + langchain-core + langchain-anthropic + langchain-google-genai + langsmith（5 个） | 零框架依赖（自研） |
| 依赖链深度 | 浅（pydantic-ai → pydantic） | 深（5 个 LangChain 包 + 各自的传递依赖） | 浅（litellm 做 LLM 路由） |
| 上游 breaking change 风险 | 低（Pydantic 公司风格稳健） | 高（LangChain API 变动频繁，历史教训多） | 低（自己控制节奏） |
| 升级适配成本 | 低（3 个导入点） | 中（LangGraph 图结构可能变） | 低（Crew/Agent/Task 三个类稳定） |

### 2.3 LLM 集成

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 方式 | pydantic-ai Model 标识符 | provider:model 字符串 + LangChain init_chat_model() | LiteLLM 统一路由 |
| 默认模型 | anthropic:claude-opus-4-6 | anthropic:claude-sonnet-4-6 | 无默认（用户指定） |
| 支持厂商 | pydantic-ai 生态（26 个 provider） | LangChain 生态全覆盖 | LiteLLM 覆盖（100+ provider） |
| Prompt Caching | Anthropic 自动启用 | Anthropic 自动启用 | 无内置 |
| Thinking 模式 | 支持（effort 可配） | 支持（per-provider profiles） | 支持（reasoning=True） |
| 特色 | 子代理自动用便宜模型 | per-provider profiles 自动配置 | LLM 厂商覆盖最广 |

### 2.4 工具系统

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 注册方式 | @tool 装饰器 + FunctionToolset | BackendProtocol 内置工具 + 中间件注入 | @tool 装饰器 + BaseTool 子类 |
| 内置工具 | write_todos, read_file, write_file, edit_file, ls, glob, grep, execute, task, skills | write_todos, read_file, write_file, edit_file, ls, glob, grep, execute, task | 30+ 预置工具（搜索/爬虫/PDF/CSV/代码解释器等） |
| 工具分组 | ToolsetConfig | 无显式分组，中间件控制可见性 | 按 Agent 分配 |
| 中间件 | Hooks（8 事件类型） | 洋葱模型中间件栈（11 个） | 无工具中间件 |
| MCP 支持 | 无原生（通过 pydantic-ai FastMCPToolset） | langchain-mcp-adapters | 原生 mcps=[] 参数 |
| 异步执行 | 无 | 支持 async_task() | 支持 async_execution |
| 缓存 | 无 | 无 | 内置工具缓存（可自定义缓存函数） |
| 特色 | Skills 三阶段渐进加载 | BackendProtocol 统一文件操作 | 预置工具最多，开箱即用 |

### 2.5 MCP 集成对比

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| MCP 支持 | 无原生（通过 pydantic-ai FastMCPToolset） | langchain-mcp-adapters | 原生 mcps=[] 参数 |
| 集成方式 | Toolset 级别 | 适配器转换 | Agent 级别直接声明 |
| 粒度 | 服务器级 | 服务器级 | 服务器级 + 单工具级（#tool_name） |
| Catalog | 无 | 无 | 支持（连接名直接引用） |

CrewAI 的 MCP 集成是三者中最优雅的：

```python
agent = Agent(
    role="Research Analyst",
    mcps=[
        "https://mcp.exa.ai/mcp?api_key=xxx",      # 完整 MCP 服务器
        "https://api.weather.com/mcp#get_forecast",  # URL + 指定工具
        "snowflake",                                  # Catalog 连接的 MCP
        "stripe#list_invoices"                        # Catalog MCP + 指定工具
    ]
)
```

### 2.6 沙箱执行

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 方式 | Backend 路由：State/Local/Docker/Composite | BackendProtocol：State/Filesystem/LocalShell/Composite + 合作伙伴 | 无内置沙箱（推荐 E2B/Modal 外部集成） |
| 隔离级别 | 组合策略 | State(内存,最安全) → LocalShell(需 opt-in) | 依赖外部服务 |
| 合作伙伴 | 无 | Daytona/Modal/QuickJS/Runloop | E2B/Modal（通过 crewai-tools） |
| 安全审计 | 无 | 无（有 THREAT_MODEL.md 文档） | 无 |
| 特色 | 组合灵活 | 抽象最干净，零改动切换环境 | 最轻量（不内置=不承担风险） |

### 2.7 子代理 / 委派

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 方式 | 3 角色 + 自定义 + task() 工具 | SubAgentMiddleware + task()/async_task() | Agent 间 Task 传递 + allow_delegation |
| 上下文隔离 | clone_for_subagent() 共享 backend，隔离 todos | _EXCLUDED_STATE_KEYS 状态键过滤 | 每个 Agent 独立 memory + context |
| 并行执行 | 无 | 支持 async_task() 并行 | Process.hierarchical 支持委派 |
| 嵌套深度 | max_nesting_depth=1（可配） | 可配 | 无限制（但有 max_iter 兜底） |
| 特色 | 简单可控 | 隔离最显式 | 角色协作最自然 |

### 2.8 记忆系统

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 工作记忆 | 文件级（MEMORY.md） | 文件级（AGENTS.md 多层覆盖） | 内置 ShortTermMemory |
| 长期记忆 | 无 | 无（Agent 通过 edit_file 自更新） | LongTermMemory（SQLite） |
| 实体记忆 | 无 | 无 | EntityMemory（实体关系提取） |
| 用户记忆 | 无 | 无 | UserMemory（跨会话用户偏好） |
| 存储后端 | Backend 文件系统 | Backend 文件系统 | 内置 SQLite + 可配 Embedder |
| 压缩 | EvictionProcessor + ContextManagerCapability | SummarizationMiddleware（两阶段：截断+摘要） | respect_context_window 自动摘要 |
| 特色 | 简单可靠 | 两阶段压缩最精细 | 记忆类型最丰富（4 种） |

### 2.9 上下文管理

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 压缩触发 | ContextManagerCapability 自动（token 阈值） | 三种触发（消息数/token 数/上下文比例） | respect_context_window（token 阈值） |
| 压缩策略 | LLM 摘要 + 大输出驱逐到文件 | 先参数截断再 LLM 摘要 + 历史持久化到 markdown | LLM 摘要或停止执行 |
| Token 计数 | 框架内置（模型感知） | model profiles 计算 | 内置（模型感知） |
| 手动压缩 | 无 | compact_conversation 工具 | 无 |
| 特色 | 大输出驱逐独特 | 自动+手动双模式 | 简单直接 |

---

## 3. 功能矩阵对比

| 功能维度 | Pydantic-Deep | Deep Agents | CrewAI | 最佳选择 |
|---------|--------------|-------------|--------|---------|
| 作为库嵌入 | create_deep_agent() | create_deep_agent() | Crew() | 三者持平 |
| 多 Agent 编排 | task() 委派 | SubAgentMiddleware | Crew + Process | CrewAI |
| 工作流引擎 | 无 | 无 | Flow(@start/@listen/@router) | CrewAI（独有） |
| 中间件架构 | Hooks（8 事件） | 洋葱模型（11 个中间件） | 无 | Deep Agents |
| 沙箱抽象 | Backend 路由 | BackendProtocol（5 种 + 合作伙伴） | 无内置 | Deep Agents |
| Skills 系统 | 三阶段渐进加载 | agentskills.io 规范 | 无 | Pydantic-Deep |
| 成本追踪 | USD 预算强制执行 | LangSmith | 无内置 | Pydantic-Deep |
| 预置工具数量 | ~10 个 | ~10 个 | 30+ 个 | CrewAI |
| MCP 支持 | 无原生（Toolset 级） | langchain-mcp-adapters | 原生 mcps=[] 参数 | CrewAI |
| 记忆类型 | 1 种（文件） | 1 种（文件） | 4 种（短期/长期/实体/用户） | CrewAI |
| 结构化输出 | Pydantic Model | Pydantic + TypedDict | Pydantic Model | 三者持平 |
| Checkpoint/Rewind | 有 | LangGraph 检查点 | 无 | Pydantic-Deep / Deep Agents |
| 安全威胁文档 | 无 | THREAT_MODEL.md（9 项） | 无 | Deep Agents |
| 权限控制 | Hooks | PermissionsMiddleware（glob 规则） | 无 | Deep Agents |
| 人机协作 | 无 | human-in-the-loop 审批 | human_input=True | Deep Agents / CrewAI |
| 商业版 SaaS | 无 | LangSmith（追踪） | CrewAI Enterprise（全套） | CrewAI |
| 遥测/隐私 | 无遥测 | LangSmith 可选 | 默认匿名遥测（可关闭） | Pydantic-Deep |

---

## 4. 核心数据流对比

### 4.1 Pydantic-Deep

```
用户输入 → CLI / Python API
  → create_deep_agent(model, instructions, tools, toolsets, capabilities, ...)
    → 组装 Toolsets: Todo + Console + Subagent + Skills + Memory + Context
    → 组装 Capabilities: Hooks + Checkpoint + ContextManager + CostTracking
    → 组装 Processors: Eviction + Patch + Summarization
  → Agent.run() 进入 Agentic Loop
    → dynamic_instructions() 注入运行时状态
    → LLM 调用 → 工具执行（通过 Backend）→ 结果回传
    → EvictionProcessor 驱逐大输出
    → ContextManagerCapability 自动压缩（超阈值时）
    → 如需委派：task() → 子 Agent 隔离执行 → 单一结果返回
  → Checkpoint 保存 → Memory 更新 → 成本上报
```

### 4.2 Deep Agents

```
用户输入 → CLI(Textual TUI) / ACP(编辑器) / SDK
  → create_deep_agent(model, tools, middleware, backend, ...)
    → 组装中间件栈（严格三段排序）
      → base: [Permissions, Skills, Memory]
      → user: [自定义中间件...]
      → tail: [Subagents, AsyncSubagents, Summarization, PatchToolCalls]
    → 编译为 LangGraph CompiledGraph
  → LangGraph Agent Loop
    → middleware.before_agent() [正序]
    → LLM 调用 → 工具执行（通过 BackendProtocol）→ 结果回传
    → middleware.wrap_tool_call() [洋葱模型]
    → SummarizationMiddleware 自动压缩（先截断再摘要）
    → 如需委派：task() → 子 Agent 状态键过滤隔离 → 单一结果返回
    → middleware.after_agent() [逆序]
  → LangSmith 追踪上报
```

### 4.3 CrewAI

```
用户输入 → Python SDK / CLI
  → Crew(agents=[...], tasks=[...], process=sequential|hierarchical)
  → crew.kickoff()
    → Process 编排器按顺序/层级分配 Task
    → 每个 Task:
      → Agent 接收任务描述 + context（前序 Task 输出）
      → LLM 调用（通过 LiteLLM）→ 工具执行 → 结果回传
      → respect_context_window 自动摘要（超阈值时）
      → allow_delegation=True 时可委派给其他 Agent
      → Memory 更新（短期/长期/实体/用户）
    → 所有 Task 完成 → 汇总结果
  → CrewOutput（包含 token 使用统计）

Flow 模式（独有）:
  @start() → 触发入口
  @listen(task_a) → 监听事件
  @router(task_b) → 条件路由
  or_(a, b) / and_(a, b) → 逻辑组合
```

---

## 5. 稳定性分析 & 潜在 Bug

### 5.1 Pydantic-Deep v0.3.3

已发现 14 个问题（4 P0 + 4 P1 + 6 P2）

| 级别 | # | 位置 | 问题 | 影响 |
|------|---|------|------|------|
| P0 | 1 | agent.py:961 | agent.tool(tool.function) 注册用户工具丢失 Tool 元数据 | prepare/validator/max_retries 被静默丢弃 |
| P0 | 2 | agent.py:966-967 | Agent 实例上 setattr 私有属性 _context_middleware | pydantic-ai 升级加 __slots__ 时断裂 |
| P0 | 3 | checkpointing.py:362 | request_context.messages 访问 Any 类型属性 | pydantic-ai 改结构时静默失败 |
| P0 | 4 | FileCheckpointStore 全部方法 | async def 内部同步 I/O（path.read_bytes()） | 高并发阻塞事件循环 |
| P1 | 5 | deps.py:43-46 | 访问 backend._files 私有属性 + object.setattr hack | StateBackend 重构时断裂 |
| P1 | 6 | eviction.py vs memory.py | write() 参数类型不一致（str vs bytes） | 某个调用方可能类型错误 |
| P1 | 7 | eviction.py:171 | _evicted_ids 共享 set 并发不安全 | 多线程场景 RuntimeError |
| P1 | 8 | checkpointing.py:177 | remove_oldest() 依赖 dict 插入顺序 | 用户标记的重要 checkpoint 被意外删除 |
| P2 | 9 | hooks.py:250 | 模块中间重复导入 | 代码拼接痕迹 |
| P2 | 10 | hooks.py:197 | asyncio.to_thread 假设 execute() 同步 | 异步 backend 时错误执行 |
| P2 | 11 | hooks.py:291 | asyncio.create_task() 未追踪 | GC 警告或内存泄漏 |
| P2 | 12 | history_archive.py:117 | except Exception 吞掉所有异常 | 文件损坏时静默返回空 |
| P2 | 13 | skills/toolset.py:220 | 默认 ./skills 相对路径 | 不同工作目录行为不一致 |
| P2 | 14 | checkpointing.py:299 | list(messages) 浅拷贝 | 依赖 ModelMessage 不可变性假设 |

### 5.2 Deep Agents v0.5.3

已发现 7 个问题（3 P0 + 2 P1 + 2 P2）

| 级别 | # | 位置 | 问题 | 影响 |
|------|---|------|------|------|
| P0 | 1 | THREAT_MODEL T1 | Memory/Skill 文件注入无 sanitization | prompt injection 劫持 Agent |
| P0 | 2 | THREAT_MODEL T3 | LocalShellBackend shell=True 无审计 | 任意命令执行 |
| P0 | 3 | 版本 v0.5.x | 8 天 3 个 release，API 极不稳定 | 生产环境升级风险极高 |
| P1 | 4 | THREAT_MODEL T8 | 异步子代理输出注入无 sanitization | 远程服务被攻击时注入恶意指令 |
| P1 | 5 | permissions.py | 无匹配规则默认允许（fail-open） | 忘记配置的路径默认可读可写 |
| P2 | 6 | graph.py | 单函数 635 行 | 可维护性差 |
| P2 | 7 | 依赖链 | 5 个 LangChain 包 | 升级风险高 |

### 5.3 CrewAI v1.14.1

基于文档和公开信息的分析（未做源码级审计）

| 级别 | # | 问题 | 影响 |
|------|---|------|------|
| P1 | 1 | 默认匿名遥测（OTEL_SDK_DISABLED=true 关闭） | 企业环境可能不接受默认开启遥测 |
| P1 | 2 | 内置代码执行已弃用（推荐外部沙箱） | 过渡期可能有兼容性问题 |
| P1 | 3 | 无内置沙箱和命令审计 | 代码执行安全依赖外部服务 |
| P2 | 4 | 无中间件/Hook 系统 | 工具调用无法拦截或审计 |
| P2 | 5 | 迭代快但 v1.x API 相对稳定 | 风险可控 |

---

## 6. 维护成本对比

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 框架 bug 谁修 | pydantic-deep 团队 | LangChain 团队 | CrewAI Inc. |
| 新功能谁加 | 升级包就有 | 升级包就有 | 升级包就有 |
| 上游 breaking change | pydantic-ai 帮你挡 | LangChain 5 个包任一变动都可能影响 | CrewAI 自己控制 |
| 升级方式 | `pip install -U pydantic-deep` | `pip install -U deepagents` | `pip install -U crewai` |
| 你需要维护的代码 | 胶水代码（~3 个导入点） | 胶水代码 | Agent/Task/Crew 定义 |
| 依赖链风险 | 低（1 个核心依赖） | 高（5 个 LangChain 包） | 低（自研 + LiteLLM） |
| 版本稳定性 | v0.3.3 pre-1.0（有风险） | v0.5.3 pre-1.0（风险更高） | v1.14.1（最稳定） |
| 锁版本建议 | ==0.3.3 精确锁定 | ==0.5.3 精确锁定 | ~=1.14 允许 patch |

---

## 7. 安全模型对比

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 安全文档 | 无 | THREAT_MODEL.md（9 项威胁分析） | 无 |
| 沙箱默认 | StateBackend（内存，安全） | StateBackend（内存，安全） | 无内置（推荐外部） |
| Shell 执行 | 需 SandboxProtocol backend | LocalShellBackend 需显式 opt-in | 已弃用内置，推荐 E2B/Modal |
| 文件权限 | Hooks 可拦截 | PermissionsMiddleware（glob 规则） | 无 |
| 命令审计 | 无 | 无（威胁已识别未防护） | 无 |
| 注入防护 | 无 | 无（威胁已识别未防护） | 无 |
| 凭证保护 | 无 | AGENTS.md 明确禁止存储凭证 | 遥测不收集 secrets |
| 最安全默认 | ✅ StateBackend 无 execute | ✅ StateBackend 无 execute | ✅ 无内置执行 |

---

## 8. 生产就绪度评分

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 功能完整度 | 8/10 | 8/10 | 9/10 |
| 代码质量 | 7/10 | 7/10 | 7/10 |
| 错误处理 | 6/10 | 6/10 | 6/10 |
| 类型安全 | 6/10 | 8/10 | 7/10 |
| API 稳定性 | 5/10 | 4/10 | 8/10 |
| 安全性 | 5/10 | 6/10 | 5/10 |
| 可扩展性 | 8/10 | 9/10 | 7/10 |
| 依赖健康度 | 8/10 | 5/10 | 8/10 |
| **综合** | **6.6** | **6.6** | **7.1** |

---

## 9. 实际使用体验对比

### 9.1 CrewAI 的痛点（团队实际踩坑）

CrewAI 的"显式定义角色"听起来很美，用起来很累：

```python
# CrewAI — 每换一个场景就要重新定义这一套
researcher = Agent(role="市场研究员", goal="...", backstory="...", tools=[...])
analyst = Agent(role="数据分析师", goal="...", backstory="...", tools=[...])
writer = Agent(role="报告撰写者", goal="...", backstory="...", tools=[...])

task1 = Task(description="调研竞品", agent=researcher, expected_output="...")
task2 = Task(description="分析数据", agent=analyst, context=[task1], expected_output="...")
task3 = Task(description="撰写报告", agent=writer, context=[task2], expected_output="...")

crew = Crew(agents=[researcher, analyst, writer], tasks=[task1, task2, task3], process=Process.sequential)
```

实际问题：
- **角色调优成本高**：backstory 差一个词效果就不一样，反复调试
- **Task context 传递不稳定**：经常丢信息或传太多无关内容
- **Process.hierarchical 的 manager agent 决策奇怪**：委派逻辑不可控
- **灵活性差**：换个需求就要重新编排整套 Agent/Task 定义
- **Bug 多**：团队实际使用中遇到不少框架层面的问题

### 9.2 Pydantic-Deep 的优势

```python
# Pydantic-Deep — 一行搞定，LLM 自己判断
agent = create_deep_agent(subagents=[
    {"name": "researcher", "description": "负责市场调研和竞品分析"},
    {"name": "analyst", "description": "负责数据分析和趋势判断"},
    {"name": "writer", "description": "负责报告撰写和格式化"},
])
result = await agent.run("写一份市场分析报告")
# Agent 自己决定是否拆分、找谁做、什么顺序
```

核心区别：**把编排决策从开发者转移回 LLM**。对于已有 ReasoningEngine 做模式路由的 Super-Agent 架构，这种方式更自然。

---

## 10. 选型建议：为什么 Pydantic-Deep 最适合 Super-Agent

### 10.1 架构契合度

| 维度 | 匹配度 | 原因 |
|------|--------|------|
| 编排模型 | ✅ 完美匹配 | ReasoningEngine 已做模式路由，不需要 CrewAI 的显式编排 |
| 依赖链 | ✅ 最优 | 1 个核心依赖（pydantic-ai），升级风险最低 |
| 团队经验 | ✅ 已验证 | 已踩过 CrewAI 的坑，pydantic-deep 的 task() 模式更适合 |
| 降级方案 | ✅ 已有 | `_create_fallback_agent()` 可降级到原生 pydantic-ai |
| 代码量 | ✅ 最少 | ~3 个导入点的胶水代码 |

### 10.2 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| v0.3.3 pre-1.0 API 不稳定 | 精确锁定版本 `==0.3.3`，升级前在 staging 验证 |
| P0 bug（4 个） | 已识别，可 monkey-patch 或提 PR 修复 |
| 社区规模小（~5K star） | Pydantic 公司间接背书，核心维护者活跃 |
| 无商业支持 | 代码量小（8.4K 行），团队可自行维护 fork |

### 10.3 最终结论

```
Super-Agent 选型：Pydantic-Deep ✅

理由：
1. 编排模型最匹配 — LLM 自主决定 + task() 委派 = ReasoningEngine 的天然延伸
2. 依赖最轻 — 1 个核心依赖，升级风险最低
3. 团队已验证 — 踩过 CrewAI 的坑，知道显式编排的代价
4. 降级兜底 — 随时可退回原生 pydantic-ai
5. 维护成本最低 — 8.4K 行源码，团队可完全掌控
```