## 1. 项目骨架与配置

- [x] 1.1 初始化 `src-deepagent/` 目录结构，创建所有 `__init__.py`
- [x] 1.2 创建 `src-deepagent/config/settings.py` — Pydantic BaseSettings，环境变量绑定（LLM/Redis/E2B/Langfuse/MCP 配置）
- [x] 1.3 创建 `src-deepagent/core/exceptions.py` — AgentError 基类 + ReasoningError/SubAgentError/WorkerError/BridgeError/SandboxError/SandboxTimeoutError
- [x] 1.4 创建 `src-deepagent/core/logging.py` — 结构化日志，trace_id/session_id 注入，格式 `[session_id][trace_id] message`
- [x] 1.5 `pyproject.toml` 添加 `pydantic-deep[cli]` 及子包依赖

## 2. 数据模型

- [x] 2.1 创建 `src-deepagent/schemas/agent.py` — TaskType（含 SUB_AGENT_TASK）、RiskLevel、TaskStatus、TaskNode、ExecutionDAG、WorkerResult、OrchestratorOutput（含 sub_agent_results）
- [x] 2.2 创建 `src-deepagent/schemas/api.py` — QueryRequest（mode 支持 sub_agent）、QueryResponse、EventType（含 sub_agent_started/progress/completed）
- [x] 2.3 创建 `src-deepagent/schemas/sandbox.py` — SandboxTask、SandboxResult、Artifact
- [x] 2.4 创建 `src-deepagent/sub_agents/models.py` — SubAgentInput、SubAgentOutput

## 3. LLM 配置

- [x] 3.1 创建 `src-deepagent/llm/config.py` — 模型工厂 get_model()，LiteLLM 多提供商路由，model alias（planning/execution/fast）
- [x] 3.2 创建 `src-deepagent/llm/token_manager.py` — 沙箱临时 JWT 签发（HS256, 10min TTL）

## 4. Worker 层

- [x] 4.1 创建 `src-deepagent/workers/base.py` — WorkerProtocol（runtime_checkable）+ BaseWorker（模板方法：execute → _do_execute，含日志/追踪/异常处理）
- [x] 4.2 创建 `src-deepagent/workers/native/rag_worker.py` — RAGWorker，Milvus 向量检索
- [x] 4.3 创建 `src-deepagent/workers/native/db_query_worker.py` — DBQueryWorker，SQL 只读查询（SELECT 白名单校验）
- [x] 4.4 创建 `src-deepagent/workers/native/api_call_worker.py` — APICallWorker，HTTP API 调用
- [x] 4.5 创建 `src-deepagent/workers/sandbox/sandbox_manager.py` — SandboxManager，Local/E2B 双后端，write_file/read_file/list_files/collect_artifacts
- [x] 4.6 创建 `src-deepagent/workers/sandbox/ipc.py` — Pi Agent JSONL 输出解析
- [x] 4.7 创建 `src-deepagent/workers/sandbox/sandbox_worker.py` — SandboxWorker，编排沙箱生命周期（创建→执行→销毁）

## 5. Skill 系统

- [x] 5.1 创建 `src-deepagent/skills/schema.py` — SkillMetadata、SkillInfo
- [x] 5.2 创建 `src-deepagent/skills/registry.py` — SkillRegistry 单例，三阶段渐进加载（摘要→search→execute），YAML frontmatter 解析

## 6. 推理引擎

- [x] 6.1 创建 `src-deepagent/orchestrator/reasoning_engine.py` — ExecutionMode/ComplexityLevel/ComplexityScore 枚举和数据类
- [x] 6.2 实现 ReasoningEngine._resolve_mode() — 三级分类：显式指定→规则匹配→复杂度评估
- [x] 6.3 实现 ReasoningEngine._evaluate_complexity() — 五维度规则评估（task_count/domain_span/dependency_depth/output_complexity/reasoning_depth）
- [x] 6.4 实现 ReasoningEngine._evaluate_complexity() LLM 兜底 — 模糊区间（0.35~0.55）调用 fast_model 二次判断
- [x] 6.5 实现 ReasoningEngine._resolve_resources() — 一次性获取 Workers/MCP/Skills/桥接工具，封装为 ResolvedResources
- [x] 6.6 实现 ReasoningEngine._assemble_plan() — 根据 ExecutionMode 装配 ExecutionPlan（prompt_prefix/resources）
- [x] 6.7 实现 ReasoningEngine.decide() — 组合 _resolve_mode + _resolve_resources + _assemble_plan

## 7. 桥接层

- [x] 7.1 创建 `src-deepagent/sub_agents/bridge.py` — create_worker_tools() 函数，返回桥接工具列表
- [x] 7.2 实现桥接工具 execute_rag_search — 构建 TaskNode，调用 RAGWorker.execute()
- [x] 7.3 实现桥接工具 execute_db_query — 构建 TaskNode，调用 DBQueryWorker.execute()
- [x] 7.4 实现桥接工具 execute_api_call — 构建 TaskNode，调用 APICallWorker.execute()
- [x] 7.5 实现桥接工具 execute_sandbox — 构建 SandboxTask，调用 SandboxWorker.execute()
- [x] 7.6 实现桥接工具 execute_skill / search_skills — 调用 SkillRegistry
- [x] 7.7 实现桥接工具 emit_chart — 构建 ECharts 渲染指令，推送 render_widget 事件
- [x] 7.8 实现桥接工具 recall_memory — 调用 MemoryRetriever
- [x] 7.9 实现桥接工具 plan_and_decompose — 调用 Planner Agent 生成 ExecutionDAG

## 8. Sub-Agent 配置

- [x] 8.1 创建 `src-deepagent/sub_agents/prompts.py` — RESEARCH_INSTRUCTIONS / ANALYSIS_INSTRUCTIONS / WRITING_INSTRUCTIONS
- [x] 8.2 创建 `src-deepagent/sub_agents/factory.py` — create_sub_agent_configs()，基于 bridge_tools 创建三个 SubAgentConfig（researcher/analyst/writer）

## 9. 主 Agent + Hooks

- [x] 9.1 创建 `src-deepagent/orchestrator/hooks.py` — event_push_hook（工具调用事件→Redis Stream）
- [x] 9.2 实现 loop_detection_hook — 滑动窗口(20) + MD5 去重 + 3次警告 + 5次强制停止
- [x] 9.3 实现 audit_logger_hook — 工具名/参数/耗时/结果写入结构化日志
- [x] 9.4 创建 `src-deepagent/orchestrator/prompts/system.py` — build_dynamic_instructions()，注入 Skill 摘要 + Sub-Agent 角色描述
- [x] 9.5 创建 `src-deepagent/orchestrator/prompts/planning.py` — DAG 规划 prompt，含 SUB_AGENT_TASK 类型说明
- [x] 9.6 创建 `src-deepagent/orchestrator/agent_factory.py` — create_orchestrator_agent()，基于 create_deep_agent() 创建主 Agent

## 10. 基础设施

- [x] 10.1 创建 `src-deepagent/memory/schema.py` — UserProfile / Fact / MemoryData
- [x] 10.2 创建 `src-deepagent/memory/storage.py` — MemoryStorage ABC + RedisMemoryStorage
- [x] 10.3 创建 `src-deepagent/memory/retriever.py` — MemoryRetriever（200ms 超时降级）
- [x] 10.4 创建 `src-deepagent/memory/updater.py` — MemoryUpdater（LLM 抽取 + 分布式锁 + 去重）
- [x] 10.5 创建 `src-deepagent/streaming/stream_adapter.py` — Redis Streams 适配器（XADD/XRANGE/XREAD）
- [x] 10.6 创建 `src-deepagent/streaming/sse_endpoint.py` — SSE 端点（断点续传 Last-Event-ID，15s 心跳）
- [x] 10.7 创建 `src-deepagent/monitoring/langfuse_tracer.py` — Langfuse trace/span 集成
- [x] 10.8 创建 `src-deepagent/monitoring/pipeline_events.py` — pipeline_step 上下文管理器（步骤计时/元数据）
- [x] 10.9 创建 `src-deepagent/state/session_manager.py` — SessionManager（Redis 持久化，状态机 CREATED→PLANNING→EXECUTING→COMPLETED/FAILED）

## 11. 网关与入口

- [x] 11.1 创建 `src-deepagent/gateway/rest_api.py` — POST /api/agent/query + GET /api/agent/stream/{session_id}，初始化 ReasoningEngine/SubAgentFactory/Workers
- [x] 11.2 创建 `src-deepagent/gateway/websocket_api.py` — WebSocket 双向通信端点
- [x] 11.3 创建 `src-deepagent/main.py` — FastAPI 应用工厂 + lifespan（启动时初始化 Redis/Workers/SkillRegistry，关闭时清理）

## 12. 集成验证

- [ ] 12.1 验证 DIRECT 模式：简单问题 → 主 Agent 直接回答，不触发 Sub-Agent
- [ ] 12.2 验证 AUTO 模式：中等问题 → 主 Agent 调用桥接工具执行
- [ ] 12.3 验证 SUB_AGENT 模式：复杂问题 → plan_and_decompose + task() 委派 Sub-Agent
- [ ] 12.4 验证并行场景：多个 Sub-Agent 并行执行，共享桥接工具
- [ ] 12.5 验证 SSE 事件流：sub_agent_started / sub_agent_completed 事件正确推送
