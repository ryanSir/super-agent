# Sub-Agent 架构（全栈 pydantic-deepagents）

## 概述

企业级智能体运行时，基于 pydantic-deepagents 全栈构建。支持四种执行模式，根据用户问题复杂度动态选择最优策略。

代码目录：`src_deepagent/`，与 `src/` 老代码完全隔离，独立运行在 9001 端口。

## 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 集成模式 | Agent-as-Tool | 与 PydanticAI 天然兼容，未来可扩展到 multi-agent |
| 主 Agent | pydantic-deepagents | 统一技术栈，SubAgentToolset 天然支持委派 |
| Sub-Agent | pydantic-deepagents | TodoToolset、上下文压缩、cost tracking 开箱即用 |
| 推理引擎 | ReasoningEngine（自建） | 复杂度评估+模式路由是核心差异化 |
| 复杂度评估 | 规则优先 + LLM 兜底 | 零延迟优先，模糊区间 LLM 兜底 |
| SubAgent 角色 | Research + Analysis + Writing | 代码执行继续走 SandboxWorker → Pi Agent |
| 沙箱调用 | 双通道 | 简单任务主 Agent 直接调，复杂任务 sub-agent 内部调 |
| 工具传递 | 一次获取，向下传递 | 避免 MCP 重复连接 |
| MCP 加载 | 渐进式（DeferredToolRegistry） | 只注入名称到 prompt，按需加载完整 schema |
| 提示词管理 | 模板文件分离 | 提示词与代码解耦，独立维护 |

---

## 一、架构总览

```
用户请求
  ↓
ReasoningEngine.decide(query)              ← 自建：复杂度评估 + 模式路由
  ├─ 意图理解（规则匹配）
  ├─ 复杂度评估（五维度 + LLM 兜底）
  ├─ 执行模式决策 → ExecutionMode
  ├─ 获取工具资源 → ResolvedResources（一次获取）
  │    ├─ workers（进程内引用）
  │    ├─ mcp_toolsets（网络连接）
  │    ├─ skills（内存单例）
  │    ├─ bridge_tools（10 个桥接工具）
  │    └─ deferred_tool_names（MCP 工具名称列表）
  └─ 返回 ExecutionPlan
  ↓
┌─────────────┬──────────────┬────────────────┬──────────────────┐
│   DIRECT    │     AUTO     │ PLAN_AND_EXEC  │    SUB_AGENT     │
│ 主Agent直答 │ 主Agent+工具 │ 主Agent+DAG    │ 主Agent委派子Agent│
└─────────────┴──────────────┴────────────────┴──────────────────┘
       │              │              │                  │
       └──────────────┴──────────────┴──────────────────┘
                              ↓
                   主 Agent (deepagents)
                   ├─ SubAgentToolset（内置委派）
                   ├─ TodoToolset（任务规划）
                   ├─ SummarizationProcessor（上下文压缩）
                   ├─ Cost tracking（成本追踪）
                   ├─ 桥接工具（Workers/Skills/MCP）
                   └─ subagents=[researcher, analyst, writer]
                              ↓
                   Sub-Agents (deepagents)
                   ├─ 独立上下文（clone_for_subagent）
                   ├─ 独立 TodoToolset
                   ├─ 独立 SummarizationProcessor
                   └─ 桥接工具（限定范围）
                              ↓
                   Worker Layer（自建，桥接工具背后的执行者）
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
  → 主 Agent 调 plan_and_decompose 生成 DAG:
      t1a/t1b/t1c: research(竞品A/B/C) → 并行
      t2: analyze(对比) → depends_on: [t1a,t1b,t1c]
      t3: write(报告) → depends_on: [t2]
  → 主 Agent 通过 task() 委派:
      task("researcher", "调研竞品A") ┐
      task("researcher", "调研竞品B") ├ 并行（最多3个）
      task("researcher", "调研竞品C") ┘
      task("analyst", "对比分析...", depends_on=[t1a,t1b,t1c])
      task("writer", "生成报告...", depends_on=[t2])
  → 每个 Sub-Agent 独立上下文，返回精炼结果
  → 主 Agent 综合输出
  → prompt 指令: "你是编排者，必须使用 Sub-Agent"
```
适用：可并行拆分的复杂任务。Sub-Agent 独立上下文，主 Agent 不膨胀。

### PLAN_AND_EXECUTE vs SUB_AGENT 的选择

| | PLAN_AND_EXECUTE | SUB_AGENT |
|---|---|---|
| 谁执行 | 主 Agent 自己 | Sub-Agent |
| 上下文 | 共享（会膨胀） | 隔离（干净） |
| 并行 | DAG 同层可并行 | Sub-Agent 并行 |
| 适用 | 步骤少、数据量小 | 步骤多、数据量大、可并行 |

简单说：PLAN_AND_EXECUTE 是"一个人按计划干活"，SUB_AGENT 是"一个人指挥一群人干活"。

---

## 三、目录结构

```
src_deepagent/
├── __init__.py
├── main.py                          # FastAPI 应用入口 + lifespan
│
├── config/
│   └── settings.py                  # Pydantic BaseSettings，环境变量绑定
│
├── core/
│   ├── logging.py                   # 结构化日志（trace_id/session_id 注入）
│   └── exceptions.py                # 业务异常层级（AgentError 基类）
│
├── orchestrator/                    # 编排层
│   ├── reasoning_engine.py          # 推理引擎（意图+复杂度+模式+资源获取）
│   ├── agent_factory.py             # 主 Agent 工厂（create_deep_agent）
│   ├── deferred_tools.py            # MCP 渐进式加载注册表
│   ├── hooks.py                     # Hooks（事件推送/循环检测/审计）
│   └── prompts/
│       ├── system.py                # 模板加载器（从 templates/ 读取并组装）
│       ├── planning.py              # DAG 规划 prompt
│       └── templates/               # 提示词模板（独立维护，不嵌代码）
│           ├── role.md              # 角色定义
│           ├── thinking_style.md    # 思考策略
│           ├── clarification.md     # 澄清系统
│           ├── mode_direct.md       # DIRECT 模式指导
│           ├── mode_auto.md         # AUTO 模式指导
│           ├── mode_plan_and_execute.md
│           ├── mode_sub_agent.md    # SUB_AGENT 模式指导
│           ├── tool_usage.md        # 工具使用规范
│           ├── subagent_system.md   # Sub-Agent 编排指令
│           ├── response_style.md    # 回复风格
│           └── critical_reminders.md
│
├── sub_agents/                      # Sub-Agent 层
│   ├── bridge.py                    # Worker/Skill 桥接工具（10 个）
│   ├── factory.py                   # Sub-Agent 配置工厂
│   ├── models.py                    # SubAgentInput/SubAgentOutput 契约
│   └── prompts.py                   # 角色 System Prompt
│
├── workers/                         # Worker 层（确定性执行器）
│   ├── base.py                      # WorkerProtocol + BaseWorker
│   ├── native/
│   │   ├── rag_worker.py            # Milvus 向量检索
│   │   ├── db_query_worker.py       # SQL 只读查询
│   │   └── api_call_worker.py       # HTTP API 调用
│   └── sandbox/
│       ├── sandbox_worker.py        # E2B 沙箱编排（Pi Agent 实时日志）
│       ├── sandbox_manager.py       # 沙箱生命周期（Local/E2B 双后端）
│       ├── pi_agent_config.py       # Pi Agent 启动脚本模板
│       └── ipc.py                   # Pi Agent v3 JSONL 输出解析
│
├── skills/
│   ├── registry.py                  # 三阶段渐进加载注册表
│   └── schema.py                    # SkillMetadata / SkillInfo
│
├── memory/                          # 记忆系统（Redis）
│   ├── storage.py                   # MemoryStorage ABC + RedisMemoryStorage
│   ├── retriever.py                 # 记忆检索（200ms 超时降级）
│   ├── updater.py                   # LLM 抽取 + 分布式锁更新
│   └── schema.py                    # UserProfile / Fact / MemoryData
│
├── streaming/
│   ├── stream_adapter.py            # Redis Streams 适配器
│   └── sse_endpoint.py              # SSE 端点（断点续传）
│
├── monitoring/
│   ├── langfuse_tracer.py           # Langfuse 集成
│   └── pipeline_events.py           # 管道事件（步骤计时/元数据）
│
├── gateway/
│   ├── rest_api.py                  # REST 端点
│   └── websocket_api.py             # WebSocket 端点
│
├── state/
│   └── session_manager.py           # 会话状态机（Redis 持久化）
│
├── llm/
│   ├── config.py                    # 模型工厂（OpenAIModel + OpenAIProvider）
│   └── token_manager.py             # 沙箱临时 JWT
│
└── schemas/
    ├── agent.py                     # TaskNode/ExecutionDAG/OrchestratorOutput
    ├── api.py                       # QueryRequest/QueryResponse/EventType
    └── sandbox.py                   # SandboxTask/SandboxResult/Artifact
```

---

## 四、System Prompt 架构

提示词与代码分离，模板文件在 `prompts/templates/` 目录独立维护。

### 组装结构（参考 DeerFlow 2.0 XML 标签体系）

```
<role>                          ← role.md
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

| 模式 | execution_mode 模板 | Sub-Agent 段落 | 工具可见性 |
|------|---------------------|---------------|-----------|
| DIRECT | mode_direct.md（不要规划，不要委派） | 不注入 | 隐藏 plan_and_decompose |
| AUTO | mode_auto.md（完整 DO/DON'T 规则） | 注入（LLM 自主决定） | 全量 |
| PLAN_AND_EXECUTE | mode_plan_and_execute.md（必须先规划） | 不注入 | 全量 |
| SUB_AGENT | mode_sub_agent.md（必须委派） | 注入（强制使用） | 全量 |

---

## 五、工具体系

### 三层结构

```
LLM 看到的 Tool Schema    →    桥接工具函数（bridge.py）    →    Worker 实例
─────────────────────         ──────────────────────         ──────────────
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

搜索模式：
- `"select:name1,name2"` → 精确匹配
- `"+keyword"` → 名称包含
- `"keyword"` → 正则匹配 name + description

### Skill 三阶段渐进加载

```
Stage 1: 启动时扫描 → get_skill_summary() 注入 prompt（紧凑摘要）
Stage 2: Agent 调 search_skills("论文") → 返回完整 doc_content
Stage 3: Agent 调 execute_skill("baidu-search", params) → 注入文件到沙箱 → Pi Agent 执行
```

---

## 六、请求完整流程

```
1. POST /api/agent/query {query, mode, context}
   ↓
2. Gateway 生成 session_id, trace_id
   ↓
3. ReasoningEngine.decide(query, mode)
   ├─ _resolve_mode() → ExecutionMode（三级分类）
   ├─ _evaluate_complexity() → ComplexityScore（五维度加权）
   ├─ _resolve_resources() → ResolvedResources（一次获取，含 deferred_tool_names）
   └─ _assemble_plan() → ExecutionPlan
   ↓
4. create_orchestrator_agent(plan, sub_agent_configs)
   → build_dynamic_instructions(execution_mode=plan.mode)
   → 从 templates/ 加载对应模式的提示词模板
   → create_deep_agent() 创建主 Agent
   ↓
5. agent.run(effective_query, deps=deps)
   ├─ DIRECT: 主 Agent 直接回答或调桥接工具
   ├─ AUTO: 主 Agent 自主判断调哪些工具
   ├─ PLAN_AND_EXECUTE: plan_and_decompose → 按 DAG 顺序执行
   └─ SUB_AGENT: task("researcher", ...) 委派
       → SubAgentToolset 自动创建 sub-agent（clone_for_subagent）
       → sub-agent 独立执行（独立上下文 + TodoToolset）
       → 返回精炼结果
       → 主 Agent 综合输出
   ↓
6. 事件推送 → Redis Stream → SSE → 前端
   ↓
7. 返回 OrchestratorOutput
```

---

## 七、Sub-Agent 并发控制

- 配置项：`MAX_CONCURRENT_SUBAGENTS=3`（默认）
- System Prompt 注入并发限制指令
- Sub-Agent 禁止嵌套（`include_subagents=False`）
- 超过限制时分批执行

---

## 八、编码规范

- Python 3.11+，全面使用 type hints（PEP 604 `X | Y`）
- 所有公开接口必须有 docstring（Google style）
- Pydantic v2 BaseModel，字段用 `Field()` 标注描述
- async/await 全异步，不混用同步阻塞调用
- 结构化日志，携带 trace_id/session_id
- 异常必须继承自 `AgentError`，不裸抛 Exception
- 配置统一走 `settings.py`，不硬编码
- 提示词统一放 `prompts/templates/`，不嵌入代码

---

## 九、启动方式

```bash
# 后端（端口 9001）
python run_deepagent.py

# 前端（端口 5173）
cd frontend-deepagent && npm install && npm run dev
```

老服务 `python run_server.py` 在 9000 端口，两者互不干扰。
