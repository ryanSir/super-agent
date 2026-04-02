## Why

当前架构的横切关注点（token 监控、循环检测、摘要压缩、澄清处理等）散落在 Gateway middleware 和 Orchestrator 内部逻辑中，缺乏统一的 Agent 级别中间件管道。同时，Skill 系统在每次请求时全量注入 system prompt，浪费 token；会话状态仅存于内存，无法跨会话积累用户画像和知识。参考字节 deer-flow 项目的成熟设计，引入 Agent Middleware Pipeline、渐进式 Skill 加载、跨会话记忆三大能力，提升架构的可扩展性、token 效率和用户体验。

## What Changes

- 新增 Agent Middleware Pipeline：在 Orchestrator Agent 外层包裹可插拔的中间件链，处理 token 监控、循环检测、摘要压缩、澄清处理、工具错误恢复等横切关注点
- 新增跨会话记忆子系统：支持用户画像持久化和知识积累，跨会话复用上下文
- 改造 Skill 加载机制：从全量注入改为渐进式按需加载，仅在 Agent 判断需要时才将 Skill 定义注入上下文
- 改造 Orchestrator：集成 middleware 管道，支持 memory 读写工具，支持渐进式 skill 上下文注入
- 改造 Streaming 层：新增 memory 相关事件类型，支持 middleware 产生的中间事件

## Non-goals

- 不替换 PydanticAI 为 LangGraph（保持现有编排引擎）
- 不引入 Local/Docker/K8s 多级沙箱（保持 E2B 单一沙箱方案）
- 不引入 IM 渠道集成（Slack/Telegram/飞书）
- 不改变现有 A2UI 协议的核心设计
- 不引入 Better Auth 或其他认证框架替换现有 JWT 方案

## Capabilities

### New Capabilities

- `agent-middleware`: Agent 级别可插拔中间件管道，支持 token 监控、循环检测、摘要压缩、澄清处理、工具错误恢复等横切关注点的统一管理
- `cross-session-memory`: 跨会话记忆子系统，支持用户画像存储、知识积累、记忆检索与更新，基于 Redis 持久化

### Modified Capabilities

- `orchestrator`: 集成 middleware 管道入口，新增 memory 读写工具，支持渐进式 skill 上下文注入
- `skills`: Skill 加载机制从全量注入改为渐进式按需加载，新增 `tool_search` 工具供 Agent 按需检索可用 Skill
- `streaming`: 新增 `memory_update` 和 `middleware_event` 事件类型

## Impact

- `src/orchestrator/` — Orchestrator Agent 需要包裹 middleware 管道，新增工具注册
- `src/middleware/` — 新增目录，存放所有 Agent middleware 实现
- `src/memory/` — 新增目录，存放记忆子系统（storage、updater、retriever）
- `src/skills/registry.py` — 改造为渐进式加载，摘要注入 + 按需全量加载
- `src/skills/executor.py` — 适配渐进式加载后的 Skill 查找逻辑
- `src/schemas/api.py` — 新增 memory/middleware 相关事件类型
- `src/streaming/` — 适配新事件类型
- `src/config/settings.py` — 新增 MemorySettings、MiddlewareSettings 配置类
- `frontend/src/engine/MessageHandler.ts` — 处理新事件类型
- 依赖新增：无新外部依赖，复用现有 Redis 基础设施
