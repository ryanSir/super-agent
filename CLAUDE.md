# Super Agent

企业级混合 AI Agent 引擎 — Python 控制面编排 + 沙箱 Pi Agent 自主执行。

## 源码结构

```
src_deepagent/          ← 后端主代码（Python 3.12 + FastAPI）
├── main.py             # FastAPI 入口 + lifespan
├── config/settings.py  # Pydantic BaseSettings，所有配置项
├── context/            # 上下文系统：System Prompt 模板组装（12段）
├── capabilities/       # 工具系统：10 内置工具 + Skills 三阶段加载 + MCP 延迟加载
├── memory/             # 记忆系统：Redis 持久化（Profile + Facts），200ms 超时降级
├── orchestrator/       # 编排核心：ReasoningEngine（五维度复杂度→四种模式路由）+ AgentFactory
├── agents/             # Sub-Agent：3 预置角色（researcher/analyst/writer）+ 自定义
├── workers/            # 执行层：native（RAG/DB/API/WebSearch）+ sandbox（E2B/Local + Pi Agent）
├── streaming/          # 事件流：Redis Stream → SSE，支持断点续传
├── gateway/            # API 网关：REST + WebSocket
├── state/              # 会话管理：Redis Hash，状态机
├── security/           # 安全：权限/沙箱策略/注入检测/审计（预留）
├── monitoring/         # 监控：Langfuse + ARMS
├── llm/                # 模型路由：Claude→Anthropic原生 / 其他→OpenAI兼容
├── billing/            # 计费（预留）
└── schemas/            # 数据模型：TaskNode, ExecutionDAG, API schema, A2UI

frontend-deepagent/     ← React 前端（TypeScript + Vite）
├── src/components/     # A2UI 动态组件（ChatMessage, ToolResultCard, DataWidget...）
└── src/engine/         # SSEClient + MessageHandler + ComponentRegistry

skill/                  ← Skill 插件目录（SKILL.md + scripts/）
```

## 关键路径

- 请求入口：`gateway/rest_api.py` → `POST /api/agent/query`
- 推理决策：`orchestrator/reasoning_engine.py` → `decide(query, mode)`
- Agent 创建：`orchestrator/agent_factory.py` → pydantic-deep 框架
- 工具注册：`capabilities/registry.py` → CapabilityRegistry
- Prompt 构建：`context/builder.py` → `build_dynamic_instructions()`
- 启动命令：`python run_deepagent.py`（端口 9001）

## 四种执行模式

- DIRECT：简单任务，直接回答或单工具调用
- AUTO：中等复杂度，LLM 自主判断是否拆分
- PLAN_AND_EXECUTE：多步骤，先 DAG 规划再按序执行
- SUB_AGENT：高复杂度，DAG + task() 委派给专业 Sub-Agent

## 开发约定

- Agent 框架：PydanticAI + pydantic-deep（不用 LangChain）
- 配置：全部走 Pydantic BaseSettings + .env 环境变量
- 异步优先：所有 I/O 操作用 async/await
- 工具加载：渐进式（摘要→详情→执行），不要全量注入 Prompt
- 沙箱：开发用 local（E2B_USE_LOCAL=true），生产用 E2B Cloud

## 详细文档

深入了解架构细节请查阅 `arch-doc/` 目录。
