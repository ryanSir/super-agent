## 1. 基础层：config、core、schemas

- [x] 1.1 为 `src/config/settings.py` 添加模块 docstring 和各配置类的类 docstring
- [x] 1.2 为 `src/core/exceptions.py` 添加模块 docstring 和各异常类的说明注释
- [x] 1.3 为 `src/core/middleware.py` 添加模块 docstring 和中间件函数的 docstring
- [x] 1.4 为 `src/core/dependencies.py` 添加模块 docstring 和依赖注入函数的 docstring
- [x] 1.5 为 `src/core/logging.py` 添加模块 docstring 和日志配置的行内注释
- [x] 1.6 为 `src/schemas/agent.py` 添加模块 docstring 和各数据模型的类 docstring
- [x] 1.7 为 `src/schemas/api.py` 添加模块 docstring 和请求/响应模型的类 docstring
- [x] 1.8 为 `src/schemas/sandbox.py` 添加模块 docstring 和沙箱相关模型的类 docstring
- [x] 1.9 为 `src/schemas/a2ui.py` 添加模块 docstring 和 A2UI 渲染指令模型的类 docstring

## 2. 数据层：memory、llm、mcp

- [x] 2.1 为 `src/memory/schema.py` 添加模块 docstring 和记忆数据模型的类 docstring
- [x] 2.2 为 `src/memory/storage.py` 添加模块 docstring 和 Redis 存储方法的 docstring
- [x] 2.3 为 `src/memory/retriever.py` 添加模块 docstring 和检索逻辑的行内注释（超时策略）
- [x] 2.4 为 `src/memory/updater.py` 添加模块 docstring 和 LLM 事实提取逻辑的行内注释
- [x] 2.5 为 `src/memory/queue.py` 添加模块 docstring 和队列机制的 docstring
- [x] 2.6 为 `src/memory/prompts.py` 添加模块 docstring 和各 prompt 模板的说明注释
- [x] 2.7 为 `src/llm/config.py` 添加模块 docstring 和模型路由配置的行内注释
- [x] 2.8 为 `src/llm/token_manager.py` 添加模块 docstring、JWT 签发方法的 docstring 和 TTL/scope 策略的行内注释
- [x] 2.9 为 `src/mcp/client.py` 添加模块 docstring 和 MCP 集成方法的 docstring

## 3. 执行层：workers

- [x] 3.1 为 `src/workers/base.py` 添加模块 docstring 和 WorkerProtocol/BaseWorker 的类 docstring
- [x] 3.2 为 `src/workers/native/rag_worker.py` 添加模块 docstring 和 RAG 检索方法的 docstring
- [x] 3.3 为 `src/workers/native/db_query_worker.py` 添加模块 docstring 和 SQL 安全校验逻辑的行内注释
- [x] 3.4 为 `src/workers/native/api_call_worker.py` 添加模块 docstring 和 HTTP 调用方法的 docstring
- [x] 3.5 为 `src/workers/sandbox/sandbox_worker.py` 添加模块 docstring 和沙箱编排逻辑的行内注释
- [x] 3.6 为 `src/workers/sandbox/sandbox_manager.py` 添加模块 docstring 和双后端路由策略的行内注释
- [x] 3.7 为 `src/workers/sandbox/pi_agent_config.py` 添加模块 docstring 和 pi 启动参数的说明注释
- [x] 3.8 为 `src/workers/sandbox/ipc.py` 添加模块 docstring 和 JSONL 解析/事件映射的行内注释

## 4. 编排层：orchestrator、middleware、state

- [x] 4.1 为 `src/orchestrator/orchestrator_agent.py` 添加模块 docstring、Agent 类 docstring 和工具注册逻辑的行内注释
- [x] 4.2 为 `src/orchestrator/planner.py` 添加模块 docstring 和 DAG 生成/拓扑排序的行内注释
- [x] 4.3 为 `src/orchestrator/router.py` 添加模块 docstring 和风险等级路由策略的行内注释
- [x] 4.4 为 `src/orchestrator/intent_router.py` 添加模块 docstring 和意图分类逻辑的 docstring
- [x] 4.5 为 `src/orchestrator/toolset_assembler.py` 添加模块 docstring 和动态工具组装逻辑的行内注释
- [x] 4.6 为 `src/orchestrator/prompts/system.py` 添加模块 docstring 和动态 prompt 拼接的行内注释
- [x] 4.7 为 `src/orchestrator/prompts/planning.py` 添加模块 docstring 和 DAG 规划 prompt 模板的说明注释
- [x] 4.8 为 `src/middleware/pipeline.py` 添加模块 docstring 和洋葱模型执行顺序/错误传播的行内注释
- [x] 4.9 为 `src/middleware/context.py` 添加模块 docstring 和 MiddlewareContext 生命周期的 docstring
- [x] 4.10 为 `src/middleware/base.py` 添加模块 docstring 和中间件基类的 docstring
- [x] 4.11 为 `src/middleware/loop_detection.py` 添加模块 docstring 和循环检测算法的行内注释
- [x] 4.12 为 `src/middleware/token_usage.py` 添加模块 docstring 和 token 统计逻辑的 docstring
- [x] 4.13 为 `src/middleware/summarization.py` 添加模块 docstring 和历史压缩策略的行内注释
- [x] 4.14 为 `src/middleware/memory_mw.py` 添加模块 docstring 和记忆注入逻辑的 docstring
- [x] 4.15 为 `src/middleware/tool_error_handling.py` 添加模块 docstring 和错误处理策略的行内注释
- [x] 4.16 为 `src/state/workflows.py` 添加模块 docstring 和 Temporal Workflow 各阶段的行内注释
- [x] 4.17 为 `src/state/activities.py` 添加模块 docstring 和各 Activity 函数的 docstring
- [x] 4.18 为 `src/state/session_manager.py` 添加模块 docstring 和状态机转换逻辑的行内注释
- [x] 4.19 为 `src/state/temporal_worker.py` 添加模块 docstring 和 Worker 启动配置的说明注释

## 5. 接入层：gateway、streaming、monitoring

- [x] 5.1 为 `src/gateway/rest_api.py` 添加模块 docstring 和各 REST 端点的 docstring
- [x] 5.2 为 `src/gateway/websocket_api.py` 添加模块 docstring 和 WebSocket 连接管理的行内注释
- [x] 5.3 为 `src/gateway/auth.py` 添加模块 docstring 和 JWT 认证逻辑的 docstring
- [x] 5.4 为 `src/gateway/router.py` 添加模块 docstring 和路由注册的说明注释
- [x] 5.5 为 `src/streaming/sse_endpoint.py` 添加模块 docstring 和断点续传逻辑的行内注释
- [x] 5.6 为 `src/streaming/stream_adapter.py` 添加模块 docstring 和 Redis Streams 适配逻辑的行内注释
- [x] 5.7 为 `src/streaming/ws_manager.py` 添加模块 docstring 和 WebSocket 管理器的 docstring
- [x] 5.8 为 `src/monitoring/trace_context.py` 添加模块 docstring 和 ContextVar 分布式追踪的行内注释
- [x] 5.9 为 `src/monitoring/execution_metrics.py` 添加模块 docstring 和指标采集方法的 docstring
- [x] 5.10 为 `src/monitoring/langfuse_tracer.py` 添加模块 docstring 和 Langfuse 集成的 docstring
- [x] 5.11 为 `src/monitoring/otel_setup.py` 添加模块 docstring 和 OpenTelemetry 配置的说明注释
- [x] 5.12 为 `src/monitoring/pipeline_events.py` 添加模块 docstring 和管道事件追踪的 docstring
- [x] 5.13 为 `src/main.py` 添加模块 docstring 和应用启动流程的行内注释

## 6. 技能层：skills

- [x] 6.1 为 `src/skills/registry.py` 添加模块 docstring 和技能发现/注册逻辑的行内注释
- [x] 6.2 为 `src/skills/executor.py` 添加模块 docstring 和技能执行方式（Agent 驱动/直接脚本）的行内注释
- [x] 6.3 为 `src/skills/creator.py` 添加模块 docstring 和技能创建/脚手架的 docstring
- [x] 6.4 为 `src/skills/schema.py` 添加模块 docstring 和技能数据模型的类 docstring
- [x] 6.5 为 `src/skills/init_skill.py` 添加模块 docstring
- [x] 6.6 为 `src/skills/package_skill.py` 添加模块 docstring
- [x] 6.7 为 `src/skills/quick_validate.py` 添加模块 docstring
- [x] 6.8 为 `skill/baidu-search/scripts/search.py` 添加文件头注释（功能、参数、输出格式）
- [x] 6.9 为 `skill/ai-ppt-generator/scripts/generate_ppt.py` 添加文件头注释（功能、参数、输出格式）
- [x] 6.10 为 `skill/ai-ppt-generator/scripts/random_ppt_theme.py` 添加文件头注释
- [x] 6.11 为 `skill/ai-ppt-generator/scripts/ppt_theme_list.py` 添加文件头注释

## 7. 前端层：engine + components

- [x] 7.1 为 `frontend/src/App.tsx` 添加 JSDoc（主应用组件、SSE 订阅逻辑）
- [x] 7.2 为 `frontend/src/engine/SSEClient.ts` 添加 JSDoc（断点续传、重连策略）
- [x] 7.3 为 `frontend/src/engine/MessageHandler.ts` 添加 JSDoc（A2UI 事件到 UI 状态的映射）
- [x] 7.4 为 `frontend/src/engine/ComponentRegistry.tsx` 添加 JSDoc（动态组件注册中心）
- [x] 7.5 为 `frontend/src/components/ResponseBlock.tsx` 添加 JSDoc（响应容器渲染流程）
- [x] 7.6 为 `frontend/src/components/ChatMessage.tsx` 添加 JSDoc
- [x] 7.7 为 `frontend/src/components/DataWidget.tsx` 添加 JSDoc（ECharts 数据可视化）
- [x] 7.8 为 `frontend/src/components/ArtifactPreview.tsx` 添加 JSDoc
- [x] 7.9 为 `frontend/src/components/TerminalView.tsx` 添加 JSDoc（xterm 终端模拟）
- [x] 7.10 为 `frontend/src/components/ToolResultCard.tsx` 添加 JSDoc
- [x] 7.11 为 `frontend/src/components/StepsTimeline.tsx` 添加 JSDoc
- [x] 7.12 为 `frontend/src/components/ThinkingSection.tsx` 添加 JSDoc
- [x] 7.13 为 `frontend/src/components/SkillMention.tsx` 添加 JSDoc
