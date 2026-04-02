Super Agent POC 技术架构全景

一、项目定位

企业级混合智能体核心引擎，融合 Python 宏观编排能力与 pi coding agent 微观自主执行能力。
核心理念：控制面与数据面隔离、深度结构化契约、零信任安全、白盒可观测。

二、系统拓扑（分层架构）

┌─────────────────────────────────────────────────────────────────────┐
│                        表现层 (Presentation)                         │
│              React 18 + TypeScript + Vite + ECharts                  │
│         A2UI 组件渲染引擎 — 后端驱动的动态 UI                          │
├─────────────────────────────────────────────────────────────────────┤
│                        网关层 (Gateway)                              │
│           FastAPI ASGI — REST / WebSocket / SSE                     │
│           JWT 认证 · RequestID 中间件 · CORS                          │
├─────────────────────────────────────────────────────────────────────┤
│                      状态守护层 (State Guardian)                      │
│         Temporal 分布式工作流 — 宕机恢复 · 重试 · 持久化                 │
├─────────────────────────────────────────────────────────────────────┤
│                      主控编排层 (Orchestrator)                        │
│         PydanticAI Agent — 意图理解 · 工具路由 · 结果整合               │
│         Middleware Pipeline — 循环检测 · Token 统计 · 记忆注入          │
├──────────────────────┬──────────────────────────────────────────────┤
│   可信执行层 (Native) │           隔离执行层 (Sandbox)                  │
│   RAG / DB / API     │     E2B 沙箱 / 本地模式 + pi agent             │
│   宿主进程内安全执行   │     同步执行，JSONL 输出解析                    │
├──────────────────────┴──────────────────────────────────────────────┤
│                      安全代理层 (LLM Proxy)                           │
│         LiteLLM 路由 · 临时 JWT Token · 多厂商模型切换                  │
├─────────────────────────────────────────────────────────────────────┤
│                      可观测层 (Observability)                         │
│         Langfuse 全链路追踪 · Token 成本 · Prompt 调试                  │
└─────────────────────────────────────────────────────────────────────┘

三、目录结构

super-agent-poc/
├── src/
│   ├── main.py                    # FastAPI 应用工厂 + 生命周期管理
│   ├── config/
│   │   └── settings.py            # 10 个配置类（App/DB/Redis/LLM/E2B/Langfuse/Temporal/MCP/Middleware/Memory）
│   ├── core/
│   │   ├── dependencies.py        # Redis 连接池 + FastAPI DI
│   │   ├── exceptions.py          # 分层异常体系（10+ 异常类型）
│   │   ├── logging.py             # 结构化日志 [request_id][trace_id]
│   │   └── middleware.py          # CORS · RequestID · 全局异常处理
│   ├── gateway/
│   │   ├── rest_api.py            # REST 端点（/query, /stream/{id}, /skills）
│   │   └── websocket_api.py       # WebSocket 双向通信（/ws/agent/{session_id}）
│   ├── orchestrator/
│   │   ├── orchestrator_agent.py  # PydanticAI 主控 Agent + 10 个 Tool + Middleware Pipeline
│   │   ├── planner.py             # DAG 规划器（LLM 生成任务拓扑）
│   │   ├── router.py              # 任务路由（风险等级 → Worker 映射）
│   │   └── prompts/
│   │       ├── system.py          # 动态 system prompt（注入 Skill 摘要 + 用户记忆）
│   │       └── planning.py        # DAG 规划 Prompt 模板
│   ├── middleware/
│   │   ├── pipeline.py            # 洋葱模型中间件管道
│   │   ├── context.py             # MiddlewareContext（贯穿请求生命周期）
│   │   ├── loop_detection.py      # 工具调用循环检测
│   │   ├── token_usage.py         # Token 用量统计
│   │   ├── summarization.py       # 对话历史压缩
│   │   ├── memory_mw.py           # 用户记忆注入
│   │   └── tool_error_handling.py # 工具错误处理
│   ├── memory/
│   │   ├── storage.py             # Redis 记忆存储（profile + facts）
│   │   ├── retriever.py           # 记忆检索（200ms 超时，格式化为 [User Context]）
│   │   ├── updater.py             # 记忆更新（LLM 提取事实）
│   │   └── schema.py              # MemoryData / UserProfile / Fact
│   ├── workers/
│   │   ├── base.py                # WorkerProtocol + BaseWorker（模板方法）
│   │   ├── native/
│   │   │   ├── rag_worker.py      # Milvus 向量检索
│   │   │   ├── db_query_worker.py # SQL 查询（仅 SELECT，禁止写操作）
│   │   │   └── api_call_worker.py # 内部微服务 HTTP 调用（httpx）
│   │   └── sandbox/
│   │       ├── sandbox_worker.py  # 沙箱编排（同步执行 + 输出解析）
│   │       ├── sandbox_manager.py # 双后端管理（local / E2B 自动路由）
│   │       ├── pi_agent_config.py # pi v0.62+ 启动配置（--print --mode json）
│   │       └── ipc.py             # pi JSONL 输出解析 → A2UI 事件转换
│   ├── skills/
│   │   ├── registry.py            # Skill 发现与注册（扫描 skill/ 目录）
│   │   ├── executor.py            # Skill 执行（Agent 驱动 / 直接脚本）
│   │   ├── creator.py             # Skill 创建与脚手架
│   │   └── schema.py              # SkillInfo / SkillExecuteRequest / SkillExecuteResult
│   ├── schemas/
│   │   ├── agent.py               # DAG / TaskNode / WorkerResult / OrchestratorOutput
│   │   ├── api.py                 # QueryRequest / QueryResponse
│   │   ├── sandbox.py             # SandboxTask / IPCMessage / SandboxResult / Artifact
│   │   └── a2ui.py                # RenderWidget / ProcessUpdate / TextStream / DataChart
│   ├── state/
│   │   ├── workflows.py           # Temporal AgentWorkflow（Plan→Execute→Collect）
│   │   ├── activities.py          # Temporal Activity（plan/native/sandbox/collect）
│   │   ├── session_manager.py     # 会话状态机（CREATED→PLANNING→EXECUTING→COMPLETED）
│   │   └── temporal_worker.py     # Temporal Worker 启动
│   ├── streaming/
│   │   ├── sse_endpoint.py        # SSE 端点（支持 Last-Event-ID 断点续传）
│   │   └── stream_adapter.py      # Redis Streams 事件适配器（持久化 + 实时尾随）
│   ├── llm/
│   │   ├── config.py              # PydanticAI + LiteLLM 模型路由
│   │   └── token_manager.py       # 沙箱临时 JWT Token 签发（HS256，10min TTL）
│   ├── mcp/
│   │   └── client.py              # MCP Server 集成（可选）
│   └── monitoring/
│       └── trace_context.py       # ContextVar 分布式追踪
├── skill/                          # Skill 包目录
│   ├── paper-search/              # 论文语义检索（validation_rag API）
│   ├── baidu-search/              # 百度 AI 搜索（需 BAIDU_API_KEY）
│   ├── ai-ppt-generator/          # AI PPT 生成（百度 AI PPT API）
│   ├── ai-patent-trend-analysis/  # 专利趋势分析
│   └── ...                        # 其他搜索变体
├── frontend/                       # React A2UI 前端
│   └── src/
│       ├── App.tsx                # 主应用（聊天界面 + SSE 订阅）
│       ├── engine/
│       │   ├── SSEClient.ts       # SSE 客户端（断点续传）
│       │   ├── MessageHandler.ts  # A2UI 事件 → UI 状态
│       │   └── ComponentRegistry.tsx # 动态组件注册中心
│       └── components/
│           ├── ResponseBlock.tsx  # 回答块容器（思考→步骤→工具→组件→文本）
│           ├── ChatMessage.tsx    # 聊天消息（Markdown 渲染）
│           ├── DataWidget.tsx     # ECharts 数据图表
│           ├── ArtifactPreview.tsx # 产物预览
│           └── TerminalView.tsx   # xterm 终端视图
└── tests/
    ├── test_connectivity.py       # 连通性测试（Skills / API / 沙箱）
    ├── test_orchestrator.py       # Orchestrator 单元测试
    ├── test_workers.py            # Worker 单元测试
    └── test_sandbox.py            # 沙箱集成测试

四、核心数据流

4.1 请求主流程

用户输入
  │
  ├─ REST: POST /api/agent/query ──→ 立即返回 session_id + trace_id
  │        GET /api/agent/stream/{id} ──→ SSE 事件流（支持断点续传）
  │
  └─ WebSocket: /ws/agent/{session_id} ──→ 双向实时通信
  │
  ▼
Gateway 层
  ├─ 生成 session_id + trace_id
  ├─ 异步启动编排任务（asyncio.create_task）
  └─ 推送 session_created 事件
  │
  ▼
Orchestrator（PydanticAI Agent + Middleware Pipeline）
  │
  ├─ Middleware before_agent（正序）
  │   ├─ TokenUsageMiddleware     ← 统计 Token 用量
  │   ├─ LoopDetectionMiddleware  ← 检测工具调用循环
  │   ├─ ToolErrorHandlingMiddleware ← 工具错误处理
  │   ├─ SummarizationMiddleware  ← 对话历史压缩
  │   └─ MemoryMiddleware         ← 注入用户记忆
  │
  ├─ Agent.run()（工具调用阶段）
  │   ├─ plan_and_decompose()     ← Planner 生成 ExecutionDAG
  │   ├─ execute_native_worker()  ← 可信 Worker（RAG/DB/API）
  │   ├─ execute_sandbox_task()   ← 沙箱 Worker（pi agent）
  │   ├─ execute_skill()          ← Skill 脚本执行
  │   ├─ search_skills()          ← 按需获取 Skill 完整定义
  │   ├─ recall_memory()          ← 检索用户历史记忆
  │   ├─ emit_chart()             ← 渲染 ECharts 图表
  │   └─ emit_widget()            ← 渲染任意前端组件
  │
  ├─ Middleware after_agent（逆序）
  │
  └─ OrchestratorOutput { answer, plan, worker_results, a2ui_frames }
  │
  ▼
流式输出（AsyncGenerator）
  ├─ 直接 yield answer token（无人为延迟）
  ├─ Fallback 1：从 worker_results 汇总
  └─ Fallback 2：流式 LLM 汇总 tool 返回内容
  │
  ▼
Streaming 层
  ├─ publish_event() → Redis Stream（stream:events:{session_id}）
  ├─ SSE 端点从 Redis Stream 实时尾随推送
  └─ 事件类型：session_created / step / tool_result / text_stream /
               render_widget / session_completed / session_failed / heartbeat
  │
  ▼
前端 A2UI 引擎
  ├─ SSEClient 接收事件（EventSource + Last-Event-ID 断点续传）
  ├─ MessageHandler.handleEvent() 更新 UIState
  └─ ResponseBlock 按序渲染：思考 → 步骤 → 工具结果 → 组件 → 文本

4.2 沙箱执行流程（pi agent v0.62+）

SandboxWorker.execute(task)
  │
  ├─ 1. 确定 API Key
  │     ├─ local 模式：直接使用 settings.llm.openai_api_key
  │     └─ E2B 模式：token_manager.issue_sandbox_token()（临时 JWT，10min TTL）
  │
  ├─ 2. sandbox_manager.create_sandbox()
  │     ├─ local 模式：tempfile.mkdtemp() 创建临时目录
  │     └─ E2B 模式：AsyncSandbox.create()（腾讯云容器）
  │
  ├─ 3. build_startup_command()  ← 生成 pi 启动脚本
  │     pi --print --mode json \
  │         --provider {SANDBOX_PI_PROVIDER} \
  │         --model {SANDBOX_PI_MODEL} \
  │         --tools read,bash,edit,write \
  │         --no-session \
  │         "{instruction}" > .pi_state.jsonl 2>&1
  │
  ├─ 4. execute_command("bash start_agent.sh")  ← 同步等待完成
  │
  ├─ 5. read_state_file()  ← 读取 pi JSONL 输出
  │
  ├─ 6. extract_final_answer()  ← 从 agent_end.messages 提取最终答案
  │     parse_jsonl() → IPCMessage[]（适配 pi v0.62+ 事件格式）
  │     ipc_to_a2ui_events() 映射：
  │       message_start(tool_use) → ProcessUpdate (executing)
  │       message_start(text)     → ProcessUpdate (thinking)
  │       agent_end               → FINAL_ANSWER
  │
  ├─ 7. collect_artifacts()  ← 回收产物文件
  └─ 8. destroy_sandbox()    ← 清理资源（临时目录 / E2B 容器）
  │
  ▼
  SandboxResult { task_id, success, final_answer, artifacts[], ipc_log[] }

4.3 沙箱双后端路由

SANDBOX_PROVIDER=local（开发/测试）
  ├─ 工作目录：/tmp/sandbox-{uuid}（运行时动态创建）
  ├─ 命令执行：asyncio.create_subprocess_shell
  ├─ API Key：直接使用宿主机 OPENAI_API_KEY
  ├─ 销毁：shutil.rmtree 清理临时目录
  └─ 注意：无安全隔离，仅用于开发

SANDBOX_PROVIDER=tencent（生产）
  ├─ 工作目录：E2B_WORK_DIR（配置固定路径）
  ├─ 命令执行：sandbox.commands.run(user="root")
  ├─ API Key：临时 JWT Token（10min TTL，scope=sandbox:llm_access）
  ├─ 销毁：sandbox.kill()
  └─ 隔离：完整容器隔离，无法访问宿主机

4.4 Middleware Pipeline（洋葱模型）

请求进入
  ↓
TokenUsageMiddleware.before_agent()     ← 记录开始时间
LoopDetectionMiddleware.before_agent()  ← 初始化循环检测窗口
ToolErrorHandlingMiddleware.before_agent()
SummarizationMiddleware.before_agent()  ← 检查历史长度，必要时压缩
MemoryMiddleware.before_agent()         ← 从 Redis 加载用户记忆，注入 query
  ↓
Agent.run()（核心执行）
  ↓
MemoryMiddleware.after_agent()          ← 异步更新用户记忆（防抖）
SummarizationMiddleware.after_agent()
ToolErrorHandlingMiddleware.after_agent()
LoopDetectionMiddleware.after_agent()
TokenUsageMiddleware.after_agent()      ← 记录 Token 用量到 Langfuse
  ↓
返回 OrchestratorOutput

4.5 Skill 渐进式加载

Stage 1：system prompt 注入 Skill 摘要（紧凑文本，所有 Skill 的 name + description）
Stage 2：Agent 调用 search_skills(query) 获取匹配 Skill 的完整 doc_content
Stage 3：Agent 调用 execute_skill(skill_name, args) 执行

Skill 目录结构：
skill/{name}/
  ├── SKILL.md          # frontmatter: name, description + 使用文档
  ├── scripts/          # 可执行脚本（.py / .sh / .js）
  └── references/       # 参考文档（自动注入执行上下文）

五、配置说明

5.1 环境变量（.env）

# LLM
OPENAI_API_KEY=...
OPENAI_API_BASE=http://your-gateway/v1
PLANNING_MODEL=claude-4.5-sonnet
EXECUTION_MODEL=claude-4.5-sonnet
FAST_MODEL=gpt-4o-mini

# 沙箱
SANDBOX_PROVIDER=local          # local / tencent / e2b
SANDBOX_PI_PROVIDER=my-gateway  # pi agent 使用的 LLM provider
SANDBOX_PI_MODEL=gpt-4o         # pi agent 使用的模型
E2B_API_KEY=...
E2B_TEMPLATE=custom-sandbox-1
E2B_DOMAIN=ap-beijing.tencentags.com
E2B_WORK_DIR=/data/e2b/workspace

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Langfuse（可选）
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=...

# 中间件
MIDDLEWARE_ENABLED=true
MIDDLEWARE_LOOP_WARN_THRESHOLD=3
MIDDLEWARE_LOOP_HARD_LIMIT=5

# 记忆
MEMORY_ENABLED=true
MEMORY_MAX_FACTS=20

5.2 模型路由

| 场景 | 配置项 | 默认值 |
|------|--------|--------|
| Orchestrator 规划 | PLANNING_MODEL | claude-4.5-sonnet |
| Worker 执行 | EXECUTION_MODEL | claude-4.5-sonnet |
| 快速汇总 | FAST_MODEL | gpt-4o-mini |
| pi agent | SANDBOX_PI_MODEL | gpt-4o |

六、核心设计模式

6.1 编排模式

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| Orchestrator-Workers | 全局架构 | 中心化层级编排，主控分发子任务 |
| ReAct | pi agent（沙箱内） | Thought → Action → Observation 微观闭环 |
| Plan-and-Execute | Orchestrator → Planner | LLM 生成全局 DAG，按拓扑序执行 |
| 洋葱中间件 | Middleware Pipeline | before/after 钩子，支持链式处理 |

6.2 工程模式

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| 模板方法 | BaseWorker | execute() 包装 _do_execute()，统一日志/追踪/异常 |
| 双后端路由 | SandboxManager | _is_local 属性自动路由，对外接口不变 |
| 渐进式加载 | Skill Registry | 摘要注入 prompt，按需获取完整定义 |
| 依赖注入 | FastAPI Depends | Settings / Redis / Worker 实例 |
| 单例 | settings / skill_registry | @lru_cache 或模块级全局实例 |
| 协议接口 | WorkerProtocol | runtime_checkable Protocol 定义 Worker 契约 |
| 状态机 | SessionManager | CREATED → PLANNING → EXECUTING → COMPLETED/FAILED |
| 服务端驱动 UI | A2UI | 后端下发 JSON 指令，前端动态渲染组件 |
| AsyncGenerator | run_orchestrator | 流式 yield token，无人为延迟 |

6.3 安全模式

| 机制 | 说明 |
|------|------|
| 零信任沙箱（E2B） | 沙箱内无真实 API Key，仅持有临时 JWT Token（10min TTL） |
| 本地模式隔离声明 | SANDBOX_PROVIDER=local 仅用于开发，无安全隔离 |
| SQL 注入防护 | DBQueryWorker 拦截 DROP/DELETE/TRUNCATE/ALTER/INSERT/UPDATE |
| 控制面隔离 | 业务编排在 Python 宿主，不可信代码在 E2B 容器 |
| scope 限定 | JWT Token scope=sandbox:llm_access，仅允许 LLM 调用 |

七、A2UI 协议（Agent-to-UI）

后端不返回静态 HTML，而是下发结构化 JSON 指令，前端作为"组件渲染引擎"动态渲染。

7.1 事件类型

| event_type | 触发时机 | 前端处理 |
|------------|----------|----------|
| session_created | 会话开始 | isProcessing=true，初始化 currentResponse |
| step | 执行步骤开始/完成/失败 | 更新 steps 列表 |
| tool_result | Worker/Skill 执行完成 | 追加到 toolResults |
| text_stream | LLM token 输出 | currentResponse.answer += delta |
| render_widget | emit_chart/emit_widget 调用 | ComponentRegistry 查找并渲染 |
| session_completed | 会话结束 | 归档 currentResponse 到 messages |
| session_failed | 会话失败 | 显示错误，partial_answer_len 记录已输出长度 |
| heartbeat | 15 秒无事件时 | 忽略，保持连接活跃 |

7.2 组件注册表

const registry = {
  DataChart,        // ECharts 数据可视化（折线/柱状/饼图/散点）
  ArtifactPreview,  // 沙箱产物预览
  ChatMessage,      // 聊天消息（Markdown）
  TerminalView,     // xterm 终端视图
}

后端下发 { event_type: "render_widget", ui_component: "DataChart", props: {...} }，前端自动查表渲染。

7.3 前端状态模型

type UIState = {
  sessionId: string
  isConnected: boolean
  isProcessing: boolean
  messages: ChatItem[]           // 历史消息
  currentResponse: {             // 当前构建的回答
    steps: StepState[]
    toolResults: ToolResultState[]
    widgets: WidgetState[]
    answer: string
    answerComplete: boolean
  } | null
  error: string | null
}

7.4 ResponseBlock 渲染顺序

1. ThinkingSection    ← 思考过程（可折叠）
2. StepsTimeline      ← 执行步骤时间线
3. ToolResultCard     ← 工具/Skill 执行结果
4. renderWidget       ← 动态组件（图表等）
5. ReactMarkdown      ← 最终文本回答（流式追加）

八、流式输出架构

8.1 SSE 主通道

客户端 GET /api/agent/stream/{session_id}
  ├─ 首次连接：Last-Event-ID=0-0，从头重放
  └─ 断线重连：浏览器自动发送 Last-Event-ID，从断点恢复

Redis Stream（stream:events:{session_id}）
  ├─ SESSION_TTL = 3600s（1 小时后自动过期）
  ├─ STREAM_MAXLEN = 5000（每会话最多保留事件数）
  └─ XREAD_BLOCK_MS = 15000（15 秒无事件发送 heartbeat）

8.2 文本流式输出

run_orchestrator() 返回 AsyncGenerator[str, None]
  ├─ 主路径：OrchestratorOutput.answer 直接 yield（无人为延迟）
  ├─ Fallback 1：worker_results 汇总后 yield
  └─ Fallback 2：_summarize_tool_results_stream() 真流式 LLM 汇总

Gateway 消费生成器：
  async for token in run_orchestrator(...):
      if token:
          await publish_event(session_id, {"event_type": "text_stream", "delta": token})

九、连通性测试

tests/test_connectivity.py 提供各组件独立测试：

# 测试所有 Skill
pytest tests/test_connectivity.py::TestSkillConnectivity -v -s

# 测试 API Worker（外网 + 内网）
pytest tests/test_connectivity.py::TestAPIWorkerConnectivity -v -s

# 测试 Milvus RAG
pytest tests/test_connectivity.py::TestRAGWorkerConnectivity -v -s

# 测试沙箱（e2b 包安装 + API Key + pi 命令 + 基础执行）
pytest tests/test_connectivity.py::TestSandboxConnectivity -v -s

# 全部
pytest tests/test_connectivity.py -v -s

十、本地开发启动

# 1. 安装依赖
pip install -r requirements.txt
npm install -g @mariozechner/pi-coding-agent  # pi agent

# 2. 配置环境
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY、SANDBOX_PROVIDER=local 等

# 3. 启动后端
python run_server.py

# 4. 启动temporal
temporal server start-dev --ui-port 8233 

# 5. 启动前端
cd frontend && npm install && npm run dev

# 6. 验证连通性
pytest tests/test_connectivity.py -v -s

⏺ 现在有三个 metrics API 可以用了：                                                       
                                                                                          
  1. GET /api/agent/metrics/overview?window=5 — 所有步骤的耗时统计概览（按 avg_ms 降序）                                             
  2. GET /api/agent/metrics/step/worker.sandbox.execute?window=10 — 查询指定步骤的详细统计                                           
  3. GET /api/agent/metrics/trace/{trace_id} — 查询某次请求的完整链路时间线                                                          
                                                                                                                                     
  示例：                                                                                                                             
                                                                                                                                   
  # 最近 5 分钟所有步骤概览
  curl http://localhost:9000/api/agent/metrics/overview
                                                                                                                                     
  # 沙箱执行步骤最近 10 分钟统计
  curl http://localhost:9000/api/agent/metrics/step/worker.sandbox.execute?window=10                                                 
                                                                                                                                     
  # 某次请求的完整链路
  curl http://localhost:9000/api/agent/metrics/trace/你的trace_id     