# Sub-Agent 架构（全栈 pydantic-deepagents）

## 概述

企业级智能体运行时，基于 pydantic-deepagents 全栈构建。支持四种执行模式，根据用户问题复杂度动态选择最优策略。

代码目录：`src_deepagent/`，与 `src/` 老代码完全隔离，独立运行在 9001 端口。

---

## 五大支柱

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │  上下文系统  │  │  工具系统    │  │  记忆系统    │           │
│   │  "知道什么"  │  │  "能做什么"  │  │  "记得什么"  │           │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │
│          │                │                │                    │
│          └────────────────┼────────────────┘                    │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │     Agentic Loop       │                         │
│              │  (deepagents 执行引擎)  │                         │
│              └────────────────────────┘                         │
│                           │                                     │
│          ┌────────────────┼────────────────┐                    │
│          ▼                ▼                ▼                    │
│   ┌─────────────┐  ┌─────────────┐                             │
│   │ Agent 协作   │  │  安全系统    │                             │
│   │ "怎么分工"   │  │  "边界在哪"  │                             │
│   └─────────────┘  └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| 支柱 | 职责 | 实现 |
|------|------|------|
| 上下文系统 | 决定模型"知道什么" | System Prompt 模板（XML 标签体系）+ 运行时上下文（Runtime Context）+ 用户记忆注入 |
| 工具系统 | 决定模型"能做什么" | 10 个桥接工具 + MCP 渐进式加载 + Skills 三阶段加载 + 自定义 Agent |
| 记忆系统 | 决定模型"记得什么" | Redis Memory（存取+LLM 抽取）+ 扩展点（consolidate 整合 / search 语义检索） |
| Agent 协作 | 决定"任务怎么分工" | 4 种执行模式 + 3 个预置角色 + 自定义 Agent 注册表 + 最多 3 并发 |
| 安全系统 | 决定"边界在哪里" | E2B 沙箱隔离 + SQL 白名单 + 临时 JWT + 循环检测（权限模型/注入防御待实现） |

---

## 核心模块

```
┌──────────────────┬──────────────────────────────────────────────────┐
│ ReasoningEngine  │ 大脑：理解意图 → 评估复杂度 → 选模式 → 获取资源  │
│                  │ 输出 ExecutionPlan，驱动整个执行流程               │
├──────────────────┼──────────────────────────────────────────────────┤
│ Agent Runtime    │ 心脏：基于 deepagents 的 Agent 执行引擎           │
│                  │ 驱动 LLM 推理 + 工具调用循环                      │
├──────────────────┼──────────────────────────────────────────────────┤
│ Sub-Agent 编排   │ 手臂：预置 + 自定义角色，独立上下文并行执行       │
│                  │ 最多 3 个并发，禁止嵌套                           │
├──────────────────┼──────────────────────────────────────────────────┤
│ 桥接层 (Bridge)  │ 神经：连接 Agent 世界和 Worker 世界               │
│                  │ 10 个桥接工具 + MCP 渐进式加载                    │
├──────────────────┼──────────────────────────────────────────────────┤
│ Worker 层        │ 手脚：实际执行（RAG检索/SQL查询/HTTP调用/沙箱）   │
│                  │ 确定性执行器，无 LLM                              │
├──────────────────┼──────────────────────────────────────────────────┤
│ Prompt 模板      │ 性格：XML 标签体系，模板文件独立维护               │
│                  │ 根据执行模式动态组装，含运行时上下文               │
├──────────────────┼──────────────────────────────────────────────────┤
│ 事件流           │ 血管：Redis Stream → SSE 实时推送                  │
│                  │ 支持断点续传，Sub-Agent 生命周期事件               │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

## 关键设计决策

| 模块 | 选型 | 理由 |
|------|------|------|
| 集成模式 | Agent-as-Tool | Sub-Agent 对主 Agent 是工具函数，未来可扩展到 multi-agent |
| Agent Runtime | pydantic-deepagents | 统一技术栈，SubAgentToolset/TodoToolset/上下文压缩开箱即用 |
| 推理引擎 | 自建 ReasoningEngine | 复杂度评估+模式路由是核心差异化，deepagents 不提供 |
| 复杂度评估 | 规则优先 + LLM 兜底 | 五维度加权零延迟，模糊区间（0.35~0.55）调 fast_model 兜底，超时 5s 降级 |
| 模式升级 | DIRECT → AUTO 自动升级 | DIRECT 执行后检测空输出/自述无法完成，自动升级到 AUTO 重试（最多一次） |
| Sub-Agent 角色 | 预置 3 个 + 自定义扩展 | 预置 Research/Analysis/Writing，用户可通过 AGENT.md 注册自定义角色 |
| 沙箱调用 | 双通道 | 简单任务主 Agent 直接调，复杂任务 sub-agent 内部调 |
| 工具资源 | 一次获取，向下传递 | ReasoningEngine 统一获取，避免 MCP 重复连接 |
| MCP 加载 | 渐进式 DeferredToolRegistry | 只注入名称到 prompt，Agent 按需 tool_search 加载完整 schema |
| 提示词 | 模板文件分离 | prompts/templates/*.md 独立维护，不嵌代码 |
| 记忆系统 | 自建 Redis Memory | deepagents 的 MEMORY.md 不适合多用户，预留 consolidate/search 扩展点 |

### Agent-as-Tool 说明

```
execute_rag_search(query="...")     ← 调 Worker（无 LLM）
execute_sandbox(instruction="...")  ← 调沙箱（有 Pi Agent）
task("researcher", instruction)     ← 调 Sub-Agent（有独立 LLM）

主 Agent 不知道也不关心背后是 Worker 还是另一个 Agent，
它只看到：传入参数 → 拿回结果。
```

未来扩展：Sub-Agent 接口自包含（SubAgentInput → SubAgentOutput），升级 multi-agent 只需加消息总线。

---

## 一、架构总览

```
用户请求
  ↓
ReasoningEngine.decide(query)
  ├─ 意图理解（规则匹配）
  ├─ 复杂度评估（五维度 + 模糊区间 LLM 兜底）
  ├─ 执行模式决策 → ExecutionMode
  ├─ 获取工具资源 → ResolvedResources（一次获取，三层结构）
  │    ├─ infra: InfraResources（底层资源）
  │    │    ├─ workers（4 个 Worker 实例，进程内引用）
  │    │    └─ mcp_toolsets（MCP 网络连接）
  │    ├─ agent_tools（10 个工具函数，基于 infra 构建）
  │    └─ prompt_ctx: PromptContext（注入 System Prompt 的文本）
  │         ├─ skill_summary（技能摘要）
  │         └─ deferred_tool_names（MCP 工具名称列表）
  └─ 返回 ExecutionPlan
  ↓
┌─────────────┬──────────────┬────────────────┬──────────────────┐
│   DIRECT    │     AUTO     │ PLAN_AND_EXEC  │    SUB_AGENT     │
│ 主Agent直答 │ 主Agent+工具 │ 主Agent+DAG    │ 主Agent委派子Agent│
└──────┬──────┴──────────────┴────────────────┴──────────────────┘
       │ 升级检查（空输出/自述无法完成）
       └──→ AUTO（最多一次，推送 mode_escalated 事件）
       │              │              │                  │
       └──────────────┴──────────────┴──────────────────┘
                              ↓
                   主 Agent (deepagents)
                   ├─ SubAgentToolset（内置委派）
                   ├─ TodoToolset（任务规划）
                   ├─ SummarizationProcessor（上下文压缩）
                   ├─ Cost tracking（成本追踪）
                   ├─ 桥接工具（Workers/Skills/MCP）
                   └─ subagents=[预置角色 + 自定义角色]
                              ↓
                   Sub-Agents (deepagents)
                   ├─ 独立上下文（clone_for_subagent）
                   ├─ 独立 TodoToolset
                   ├─ 独立 SummarizationProcessor
                   └─ 桥接工具（限定范围）
                              ↓
                   Worker Layer（桥接工具背后的执行者）
                   RAGWorker / DBWorker / APIWorker / SandboxWorker
```

---

## 二、四种执行模式详解

### DIRECT — 直接执行
```
用户: "1+1等于几"
  → ReasoningEngine: ComplexityLevel.LOW → DIRECT
  → 主 Agent 直接回答，不调工具
  → prompt 指令: "不要规划，不要委派，一步到位"
```
适用：简单问答、单次检索、翻译/总结

### AUTO — 自主判断
```
用户: "帮我搜索最新的AI论文"
  → ReasoningEngine: ComplexityLevel.MEDIUM → AUTO
  → 主 Agent 自主决定调 search_skills + execute_skill
  → prompt 指令: 完整的 DO/DON'T 判断规则
```
适用：中等任务，LLM 自主选择工具组合

### PLAN_AND_EXECUTE — 规划后执行
```
用户: "搜索论文，分析趋势，生成图表"
  → ReasoningEngine: 规则匹配到多步骤，复杂度 MEDIUM → PLAN_AND_EXECUTE
  → 主 Agent 调 plan_and_decompose 生成 DAG:
      t1: search(论文) → depends_on: []
      t2: analyze(趋势) → depends_on: [t1]
      t3: chart(图表) → depends_on: [t2]
  → 主 Agent 自己按 DAG 顺序执行 t1→t2→t3
  → prompt 指令: "必须先规划，不要委派 Sub-Agent"
```
适用：多步骤串行任务，主 Agent 自己能完成。注意：所有中间结果累积在主 Agent 上下文中。

### SUB_AGENT — 委派编排
```
用户: "对比分析三个竞品的技术架构，生成评估报告"
  → ReasoningEngine: 复杂度 HIGH → SUB_AGENT
  → 主 Agent 通过 task() 委派:
      task("researcher", "调研竞品A") ┐
      task("researcher", "调研竞品B") ├ 并行（最多3个）
      task("researcher", "调研竞品C") ┘
      task("analyst", "对比分析...")
      task("writer", "生成报告...")
  → 每个 Sub-Agent 独立上下文，返回精炼结果
  → prompt 指令: "你是编排者，必须使用 Sub-Agent"
```
适用：可并行拆分的复杂任务。Sub-Agent 独立上下文，主 Agent 不膨胀。

### 模式对比

| | PLAN_AND_EXECUTE | SUB_AGENT |
|---|---|---|
| 谁执行 | 主 Agent 自己 | Sub-Agent |
| 上下文 | 共享（会膨胀） | 隔离（干净） |
| 并行 | DAG 同层可并行 | Sub-Agent 并行 |
| 适用 | 步骤少、数据量小 | 步骤多、数据量大、可并行 |

简单说：PLAN_AND_EXECUTE 是"一个人按计划干活"，SUB_AGENT 是"一个人指挥一群人干活"。

### 模式升级机制（DIRECT → AUTO）

当 DIRECT 模式执行后发现 Agent 无法完成任务时，自动升级到 AUTO 模式重试。

```
DIRECT 执行完成
  ↓
_needs_escalation() 检查
  ├─ result 为 None → 升级
  ├─ 输出为空或 < 10 字符 → 升级
  ├─ 输出前 200 字符包含自述无法完成的信号词 → 升级
  │    （"无法直接回答"/"无法完成"/"需要使用工具" 等）
  └─ 其他情况 → 不升级，正常返回
  ↓
escalate_plan(plan, AUTO)
  ├─ 仅支持 DIRECT → AUTO 路径
  ├─ escalated_from 字段防止二次升级
  └─ 推送 mode_escalated 事件到前端
```

设计要点：
- 只检查输出前 200 字符（Agent 自述区域），避免在搜索结果正文中误匹配
- 信号词收紧为明确的自述无法完成表达，排除"需要搜索"等常见内容描述词
- 通过 `REASONING_ESCALATION_ENABLED` 环境变量可关闭

### 复杂度评估 LLM 兜底

当五维度规则评估分数落在模糊区间（默认 0.35~0.55）时，调用 fast_model 进行二次判断。

```
_evaluate_complexity(query)
  ├─ 五维度规则评估 → score
  ├─ score 在 [0.35, 0.55] 区间？
  │    ├─ 是 → _llm_classify(query, score, dimensions)
  │    │    ├─ 调 fast_model（gpt-4o-mini），5s 超时
  │    │    ├─ 返回 JSON: {"score": 0.xx, "reason": "..."}
  │    │    ├─ 超时/解析失败 → 保留规则分数（降级）
  │    │    └─ 成功 → 用 LLM 分数替换规则分数
  │    └─ 否 → 直接使用规则分数
  └─ score → ComplexityLevel → suggested_mode
```

配置项（`ReasoningSettings`，环境变量绑定）：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `REASONING_FUZZY_ZONE_LOW` | 0.35 | 模糊区间下界 |
| `REASONING_FUZZY_ZONE_HIGH` | 0.55 | 模糊区间上界 |
| `REASONING_LLM_CLASSIFY_TIMEOUT` | 5.0 | LLM 分类超时（秒） |
| `REASONING_LLM_CLASSIFY_ENABLED` | true | 是否启用 LLM 兜底 |
| `REASONING_ESCALATION_ENABLED` | true | 是否启用模式升级 |

---

## 三、目录结构

```
src_deepagent/
├── main.py                              # FastAPI 入口 + lifespan
│
├── config/
│   └── settings.py                      # Pydantic BaseSettings，环境变量绑定
│
├── core/                                # 核心基础设施（跨模块共享）
│   ├── logging.py                       # 结构化日志（trace_id/session_id 注入）
│   └── exceptions.py                    # 业务异常层级（AgentError 基类）
│
│   ── 支柱 1: 上下文系统 ──
├── context/
│   ├── builder.py                       # 上下文组装器（模板加载 + 动态组装）
│   ├── runtime.py                       # 运行时上下文（session/user/env）
│   └── templates/                       # 提示词模板（独立维护）
│       ├── role.md                      # 角色定义
│       ├── runtime_context.md           # 运行时上下文
│       ├── thinking_style.md            # 思考策略
│       ├── clarification.md             # 澄清系统
│       ├── mode_direct.md               # DIRECT 模式指导
│       ├── mode_auto.md                 # AUTO 模式指导
│       ├── mode_plan_and_execute.md     # PLAN_AND_EXECUTE 模式指导
│       ├── mode_sub_agent.md            # SUB_AGENT 模式指导
│       ├── tool_usage.md                # 工具使用规范
│       ├── subagent_system.md           # Sub-Agent 编排指令
│       ├── response_style.md            # 回复风格
│       └── critical_reminders.md        # 关键提醒
│
│   ── 支柱 2: 工具系统 ──
├── capabilities/
│   ├── registry.py                      # 统一能力注册表（CapabilityRegistry）
│   ├── base_tools.py                    # 10 个内置工具（封装 Workers/Skills/Memory）
│   ├── skills/                          # Skills 子系统
│   │   ├── registry.py                  # 三阶段渐进加载注册表
│   │   └── schema.py                    # SkillMetadata / SkillInfo
│   └── mcp/                             # MCP 子系统
│       └── deferred_registry.py         # 渐进式加载注册表
│
│   ── 支柱 3: 记忆系统 ──
├── memory/
│   ├── storage.py                       # MemoryStorage ABC（含 consolidate/search 扩展点）
│   ├── retriever.py                     # 记忆检索（200ms 超时降级）
│   ├── updater.py                       # LLM 抽取 + 分布式锁更新
│   └── schema.py                        # UserProfile / Fact / MemoryData
│
│   ── 支柱 4: Agent 协作 ──
├── orchestrator/                        # 编排层
│   ├── reasoning_engine.py              # 推理引擎（意图+复杂度+模式路由）
│   ├── agent_factory.py                 # 主 Agent 工厂
│   ├── hooks.py                         # 生命周期 Hooks（基于 pydantic-deep 框架）
│   └── planning.py                      # DAG 规划 prompt
│
├── agents/                              # Agent 定义
│   ├── factory.py                       # Sub-Agent 配置工厂（预置+自定义合并）
│   ├── models.py                        # SubAgentInput / SubAgentOutput
│   ├── roles.py                         # 预置角色 System Prompt
│   └── custom/                          # 自定义 Agent（Agent OS）
│       └── registry.py                  # AGENT.md 扫描 + 注册
│
│   ── 支柱 5: 安全系统 ──
├── security/
│   ├── permissions.py                   # 工具级权限模型（allow/deny/ask）
│   ├── sandbox_policy.py                # 沙箱安全策略（网络/文件/进程）
│   ├── injection_guard.py               # Prompt 注入检测
│   └── audit.py                         # 审计日志（工具调用链追踪）
│
│   ── 支柱 6: 全链路监控 ──
├── monitoring/
│   ├── arms_tracer.py                   # ARMS 应用监控（链路追踪）
│   ├── langfuse_tracer.py               # Langfuse 模型交互监控
│   ├── metrics.py                       # Prometheus 指标导出（→ Grafana）
│   └── pipeline_events.py              # 管道事件（步骤计时/元数据）
│
│   ── 支柱 7: 事件流 ──
├── streaming/
│   ├── protocol.py                      # 前后端数据协议定义
│   ├── stream_adapter.py                # Redis Streams 适配器
│   ├── sse_endpoint.py                  # SSE 端点
│   └── recovery.py                      # 中断恢复 + 断点续传
│
│   ── 支柱 8: LLM Provider ──
├── llm/
│   ├── provider.py                      # 多提供商管理（路由+降级+重试）
│   ├── config.py                        # 模型配置工厂
│   └── token_manager.py                 # 沙箱临时 JWT
│
│   ── 支柱 9: Token 计费 ──
├── billing/
│   ├── tracker.py                       # 用量追踪（per request/session/user）
│   ├── quota.py                         # 配额管理（限额+告警）
│   └── reporter.py                      # 用量报告（日/周/月汇总）
│
│   ── 执行层 + 网关 + 状态 + 数据模型 ──
├── workers/                             # 执行层（确定性执行器）
│   ├── base.py                          # WorkerProtocol + BaseWorker
│   ├── native/
│   │   ├── rag_worker.py                # Milvus 向量检索
│   │   ├── db_query_worker.py           # SQL 只读查询
│   │   └── api_call_worker.py           # HTTP API 调用
│   └── sandbox/
│       ├── sandbox_worker.py            # E2B 沙箱编排（Pi Agent 实时日志）
│       ├── sandbox_manager.py           # 沙箱生命周期（Local/E2B 双后端）
│       ├── pi_agent_config.py           # Pi Agent 启动脚本模板
│       └── ipc.py                       # Pi Agent v3 JSONL 输出解析
│
├── gateway/
│   ├── rest_api.py                      # REST 端点
│   └── websocket_api.py                 # WebSocket 端点
│
├── state/
│   └── session_manager.py               # 会话状态机（Redis 持久化）
│
└── schemas/
    ├── agent.py                         # TaskNode / ExecutionDAG / OrchestratorOutput
    ├── api.py                           # QueryRequest / QueryResponse
    └── sandbox.py                       # SandboxTask / SandboxResult / Artifact
```

---

## 四、上下文系统（System Prompt 架构）

提示词与代码分离，模板文件在 `prompts/templates/` 目录独立维护。

### 组装结构

```
<role>                          ← role.md（角色定义）
<runtime_context>               ← runtime_context.md（运行时上下文：session/user/time/mode）
<thinking_style>                ← thinking_style.md（先思考再行动）
<clarification_system>          ← clarification.md（CLARIFY → PLAN → ACT）
<execution_mode mode="...">     ← mode_{mode}.md（根据 ReasoningEngine 决策动态选择）
<tool_usage>                    ← tool_usage.md（10 个工具 + 安全约束）
<skill_system>                  ← 动态注入 Skill 摘要
<subagent_system>               ← subagent_system.md（仅 auto/sub_agent 模式注入）
<available_deferred_tools>      ← 动态注入 MCP 工具名称列表
<memory>                        ← 动态注入用户记忆
<response_style>                ← response_style.md
<critical_reminders>            ← critical_reminders.md
```

### 模式与 Prompt 对齐

ReasoningEngine 的代码层决策和 LLM 的 prompt 层行为完全对齐：

| 模式 | execution_mode 模板 | Sub-Agent 段落 | 工具可见性 |
|------|---------------------|---------------|-----------|
| DIRECT | mode_direct.md（不要规划，不要委派） | 不注入 | 隐藏 plan_and_decompose |
| AUTO | mode_auto.md（完整 DO/DON'T 规则） | 注入（LLM 自主决定） | 全量 |
| PLAN_AND_EXECUTE | mode_plan_and_execute.md（必须先规划） | 不注入 | 全量 |
| SUB_AGENT | mode_sub_agent.md（必须委派） | 注入（强制使用） | 全量 |

---

## 五、工具系统

### 为什么需要 Bridge 层（capabilities/base_tools.py）

Worker 和 LLM 的接口不匹配：

```
Worker 接口（面向内部，通用结构）：
  async def execute(self, task: TaskNode) -> WorkerResult
  # TaskNode 包含 task_id/task_type/risk_level/input_data 等字段
  # LLM 不知道怎么构造这个对象

LLM 工具接口（面向 LLM，语义化参数）：
  async def execute_rag_search(ctx, query: str, top_k: int = 5) -> dict
  # LLM 只需要传业务参数，不需要知道 TaskNode 结构
```

Bridge 做的事情：
1. **接口翻译** — 把 LLM 传来的业务参数（query, sql, url...）转成 Worker 需要的 TaskNode
2. **结果简化** — 把 WorkerResult 转成 dict 返回给 LLM，去掉内部字段
3. **资源注入** — Skill 执行时自动读取脚本文件注入沙箱，LLM 不需要关心文件操作
4. **错误封装** — Worker 不可用时返回友好的错误信息，而不是抛异常

Worker 保留通用接口是因为它还要支持 DAG 执行（通过 TaskNode 路由），两套接口各有用途。

### 三层结构

```
LLM 看到的 Tool Schema    →    agent_tools 函数（base_tools.py）  →    Worker 实例
─────────────────────         ──────────────────────          ──────────────
execute_rag_search            async def execute_rag_search    RAGWorker
execute_db_query              async def execute_db_query      DBQueryWorker
execute_api_call              async def execute_api_call      APICallWorker
execute_sandbox               async def execute_sandbox       SandboxWorker → Pi Agent
execute_skill                 async def execute_skill         SkillRegistry → SandboxWorker
search_skills                 async def search_skills         SkillRegistry
emit_chart                    async def emit_chart            A2UI 渲染
recall_memory                 async def recall_memory         Redis MemoryRetriever
plan_and_decompose            async def plan_and_decompose    Planner Agent
tool_search                   async def tool_search           DeferredToolRegistry
```

### MCP 渐进式加载

```
启动时：MCP 工具注册到 DeferredToolRegistry（只存名称+描述）
  ↓
System Prompt：只注入工具名称列表（<available_deferred_tools>）
  ↓
Agent 需要时：调用 tool_search("select:slack_send") 获取完整 schema
  ↓
正常调用工具
```

### Skill 三阶段渐进加载

```
Stage 1: 启动时扫描 → get_skill_summary() 注入 prompt（紧凑摘要）
Stage 2: Agent 调 search_skills("论文") → 返回完整 doc_content
Stage 3: Agent 调 execute_skill("baidu-search", params) → 注入文件到沙箱 → Pi Agent 执行
```

---

## 六、Agent 协作

### 预置角色

| 角色 | 职责 | 可用工具 |
|------|------|---------|
| researcher | 信息检索与综合分析 | rag_search, api_call, skill, search_skills, sandbox |
| analyst | 数据分析与可视化 | db_query, rag_search, sandbox, emit_chart |
| writer | 报告与文档撰写 | skill, sandbox, emit_chart + filesystem |

### 自定义 Agent

用户可通过 `agents/` 目录注册自定义 Sub-Agent：

```
agents/
├── my-data-agent/
│   └── AGENT.md
└── my-code-reviewer/
    └── AGENT.md
```

AGENT.md 格式：
```yaml
---
name: data-agent
description: 数据清洗和转换专家
model: gpt-4o-mini
tools: [execute_db_query, execute_sandbox]
---
你是一个数据处理专家，擅长数据清洗、格式转换和质量校验...
```

系统启动时 `CustomAgentRegistry.scan()` 自动发现并注册，和预置角色一起作为可用 Sub-Agent。

### 并发控制

- 配置项：`MAX_CONCURRENT_SUBAGENTS=3`
- System Prompt 注入并发限制指令
- Sub-Agent 禁止嵌套（`include_subagents=False`）
- 超过限制时分批执行

---

## 七、记忆系统

### 当前实现

- Redis Hash（用户画像）+ Sorted Set（事实，按时间排序）
- LLM 自动抽取 facts + profile（对话后异步更新）
- 200ms 超时降级（检索失败不影响主流程）
- 分布式锁防止并发更新

### 扩展点（预留）

| 扩展点 | 接口 | 用途 |
|--------|------|------|
| consolidate() | `MemoryStorage.consolidate(user_id)` | autoDream：定期整合碎片记忆为结构化摘要 |
| search() | `MemoryStorage.search(user_id, query, top_k)` | 语义检索：接入向量搜索替代全量返回 |

---

## 八、请求完整流程

```
1. POST /api/agent/query {query, mode, context}
   ↓
2. Gateway 生成 session_id, trace_id
   ↓
3. ReasoningEngine.decide(query, mode)
   ├─ _resolve_mode() → ExecutionMode（三级分类）
   ├─ _evaluate_complexity() → ComplexityScore（五维度加权 + 模糊区间 LLM 兜底）
   │    └─ 分数落在 0.35~0.55 时调 fast_model 二次判断（5s 超时降级）
   ├─ _resolve_resources() → ResolvedResources（一次获取）
   └─ _assemble_plan() → ExecutionPlan
   ↓
4. create_orchestrator_agent(plan, sub_agent_configs)
   → build_dynamic_instructions(execution_mode, runtime_context, ...)
   → 从 templates/ 加载对应模式的提示词模板
   → create_hooks(publish_fn) 创建生命周期 Hooks
   → create_deep_agent(hooks=hooks) 创建主 Agent
   ↓
5. agent.run(effective_query, deps=deps)
   ├─ DIRECT: 主 Agent 直接回答或调桥接工具
   ├─ AUTO: 主 Agent 自主判断调哪些工具
   ├─ PLAN_AND_EXECUTE: plan_and_decompose → 按 DAG 顺序执行
   └─ SUB_AGENT: task() 委派 → Sub-Agent 独立执行 → 主 Agent 综合
   ↓
5.5 模式升级检查（仅 DIRECT → AUTO，最多一次）
   ├─ 检测条件：空输出 / 过短输出 / Agent 自述无法完成
   ├─ 只检查输出前 200 字符，避免在搜索结果中误匹配
   ├─ 升级时推送 mode_escalated 事件到前端
   └─ escalated_from 字段防止二次升级
   ↓
6. 事件推送 → Redis Stream → SSE → 前端
   ↓
7. 返回 OrchestratorOutput
```

---

## 九、编码规范

- Python 3.11+，全面使用 type hints（PEP 604 `X | Y`）
- 所有公开接口必须有 docstring（Google style）
- Pydantic v2 BaseModel，字段用 `Field()` 标注描述
- async/await 全异步，不混用同步阻塞调用
- 结构化日志，携带 trace_id/session_id
- 异常必须继承自 `AgentError`，不裸抛 Exception
- 配置统一走 `settings.py`，不硬编码
- 提示词统一放 `prompts/templates/`，不嵌入代码

---

## 十、启动方式

```bash
# 后端（端口 9001）
python run_deepagent.py

# CLI 测试（无需前端）
python cli.py                              # 交互模式
python cli.py "1+1等于几"                   # 单次查询
python cli.py -m sub_agent "搜索论文并分析"  # 指定模式

# 前端（端口 5173）
cd frontend-deepagent && npm install && npm run dev
```
