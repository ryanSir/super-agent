## 1. 数据模型与配置

- [x] 1.1 在 `src/config/settings.py` 中新增 `MiddlewareSettings` 配置类（enabled, loop_warn_threshold, loop_hard_limit, loop_window_size, summarization_threshold_ratio）
- [x] 1.2 在 `src/config/settings.py` 中新增 `MemorySettings` 配置类（enabled, max_facts, debounce_seconds, update_model, redis_key_prefix）
- [x] 1.3 在 `src/schemas/api.py` 中新增 `memory_update` 和 `middleware_event` 事件类型定义

## 2. Middleware 基础设施

- [x] 2.1 创建 `src/middleware/__init__.py`
- [x] 2.2 创建 `src/middleware/base.py`，实现 `AgentMiddleware` 抽象基类（before_agent, after_agent, on_tool_call, on_tool_error 四个钩子）
- [x] 2.3 创建 `src/middleware/context.py`，实现 `MiddlewareContext` 数据类（session_id, trace_id, messages, token_usage, metadata）
- [x] 2.4 创建 `src/middleware/pipeline.py`，实现 `MiddlewarePipeline`（洋葱模型：before 正序、after 逆序执行）

## 3. Middleware 实现

- [x] 3.1 创建 `src/middleware/token_usage.py`，实现 `TokenUsageMiddleware`（after_agent 中记录 token 用量到结构化日志和 Langfuse）
- [x] 3.2 创建 `src/middleware/loop_detection.py`，实现 `LoopDetectionMiddleware`（滑动窗口 + hash 检测，warn_threshold=3 注入警告，hard_limit=5 强制终止）
- [x] 3.3 创建 `src/middleware/tool_error_handling.py`，实现 `ToolErrorHandlingMiddleware`（on_tool_error 中捕获异常转为错误消息，截断至 500 字符）
- [x] 3.4 创建 `src/middleware/summarization.py`，实现 `SummarizationMiddleware`（before_agent 中检查 token 数，超阈值时用 fast 模型压缩早期对话）
- [x] 3.5 创建 `src/middleware/memory_mw.py`，实现 `MemoryMiddleware`（after_agent 中过滤对话并提交到记忆更新队列）

## 4. 记忆子系统

- [x] 4.1 创建 `src/memory/__init__.py`
- [x] 4.2 创建 `src/memory/schema.py`，定义 `MemoryData`、`UserProfile`、`Fact` Pydantic 模型
- [x] 4.3 创建 `src/memory/storage.py`，实现 `MemoryStorage` 抽象基类和 `RedisMemoryStorage`（Redis Hash 存储 profile，Sorted Set 存储 facts）
- [x] 4.4 创建 `src/memory/updater.py`，实现 `MemoryUpdater`（LLM 提取用户画像和事实，Redis 分布式锁保证串行化）
- [x] 4.5 创建 `src/memory/retriever.py`，实现 `MemoryRetriever`（从 Redis 加载记忆，格式化为 `[User Context]` 文本，超时 200ms 降级返回空）
- [x] 4.6 创建 `src/memory/queue.py`，实现 `MemoryUpdateQueue`（防抖合并，默认 5 秒窗口，异步触发 MemoryUpdater）
- [x] 4.7 创建 `src/memory/prompts.py`，定义记忆提取和更新的 LLM prompt 模板

## 5. Skill 渐进式加载改造

- [x] 5.1 修改 `src/skills/registry.py` 中 `get_skill_summary()` 方法，仅返回名称 + 一句话描述的紧凑文本
- [x] 5.2 在 `src/skills/registry.py` 中新增 `search_skills(query: str) -> List[SkillInfo]` 方法，按关键词匹配名称和描述

## 6. Orchestrator 集成

- [x] 6.1 修改 `src/orchestrator/orchestrator_agent.py`，在 `run_orchestrator()` 入口包裹 `MiddlewarePipeline`（根据 middleware.enabled 配置决定是否启用）
- [x] 6.2 在 `src/orchestrator/orchestrator_agent.py` 中注册 `search_skills` 工具（调用 SkillRegistry.search_skills）
- [x] 6.3 在 `src/orchestrator/orchestrator_agent.py` 中注册 `recall_memory` 工具（调用 MemoryRetriever）
- [x] 6.4 修改 `src/orchestrator/prompts/system.py`，将 Skill 注入方式从全量改为摘要模式，新增 `[User Context]` 占位段落
- [x] 6.5 修改 `src/orchestrator/orchestrator_agent.py`，在 Agent 执行前调用 `MemoryRetriever` 注入用户记忆到 system prompt

## 7. Streaming 层适配

- [x] 7.1 修改 `src/streaming/stream_adapter.py`，支持 `memory_update` 和 `middleware_event` 事件类型的序列化和发布
- [x] 7.2 在各 middleware 实现中调用 `publish_event()` 发布对应事件（loop_detection 警告/终止、token_usage 报告、memory_update 完成）

## 8. 前端适配

- [x] 8.1 修改 `frontend/src/engine/MessageHandler.ts`，新增 `memory_update` 和 `middleware_event` 事件处理（忽略未知事件类型，向后兼容）

## 9. 测试

- [x] 9.1 编写 `tests/test_middleware_pipeline.py`，测试洋葱模型执行顺序、异常传播、配置开关
- [x] 9.2 编写 `tests/test_loop_detection.py`，测试滑动窗口、warn/hard_limit 触发、不同参数不触发
- [x] 9.3 编写 `tests/test_tool_error_handling.py`，测试异常捕获、消息截断、Agent 继续执行
- [x] 9.4 编写 `tests/test_memory_storage.py`，测试 Redis 存储读写、事实上限淘汰、去重、连接失败降级
- [x] 9.5 编写 `tests/test_memory_updater.py`，测试 LLM 提取、防抖合并、并发锁、失败降级
- [x] 9.6 编写 `tests/test_skill_progressive.py`，测试摘要模式输出、search_skills 匹配、无匹配返回空
