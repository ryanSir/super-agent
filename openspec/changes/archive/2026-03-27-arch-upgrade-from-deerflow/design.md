## Context

当前 super-agent-poc 采用 PydanticAI + FastAPI 的 Orchestrator-Workers 架构，横切关注点（日志、异常、CORS）仅在 Gateway 层处理，Agent 层缺乏统一的中间件管道。Skill 系统在启动时全量扫描并将摘要注入 system prompt，随着 Skill 数量增长会浪费 token。会话状态仅存于内存 `_session_histories`，无法跨会话积累用户画像。

参考字节 deer-flow 项目的成熟实现（13 层 Agent middleware、基于文件/LLM 的记忆子系统、渐进式 Skill 加载），在保持现有 PydanticAI 编排引擎不变的前提下，引入三大能力提升架构质量。

## Goals / Non-Goals

**Goals:**

- 建立 Agent 级别可插拔中间件管道，统一管理 token 监控、循环检测、工具错误恢复等横切关注点
- 实现跨会话记忆子系统，支持用户画像持久化和知识积累
- 改造 Skill 加载为渐进式按需加载，降低 token 消耗
- 所有改造向后兼容，不破坏现有 API 和前端协议

**Non-Goals:**

- 不替换 PydanticAI 为 LangGraph
- 不引入 Local/Docker/K8s 多级沙箱
- 不引入 IM 渠道集成
- 不改变 A2UI 协议核心设计
- 不替换 JWT 认证方案

## Decisions

### Decision 1: Middleware 管道基于装饰器链模式，而非 LangGraph AgentMiddleware

**选择**: 采用 Python 装饰器/包装器链模式实现 middleware 管道

**理由**: deer-flow 的 middleware 基于 LangGraph 的 `AgentMiddleware` 基类，与 LangGraph 状态机深度耦合。我们使用 PydanticAI，没有 `AgentState` 和 `Runtime` 概念。因此采用更通用的装饰器链模式：每个 middleware 包装 `run_orchestrator()` 调用，在调用前后注入逻辑。

**替代方案**:
- 直接移植 LangGraph AgentMiddleware → 需要引入 LangGraph 依赖，与现有架构冲突
- 在 FastAPI middleware 层处理 → 粒度太粗，无法访问 Agent 内部状态（如 tool_calls、token usage）

**实现方式**:

```python
# src/middleware/base.py
class AgentMiddleware(ABC):
    """Agent 级别中间件基类"""

    async def before_agent(self, context: MiddlewareContext) -> None:
        """Agent 执行前钩子"""
        pass

    async def after_agent(self, context: MiddlewareContext, result: OrchestratorOutput) -> OrchestratorOutput:
        """Agent 执行后钩子"""
        return result

    async def on_tool_call(self, context: MiddlewareContext, tool_name: str, tool_args: dict) -> dict:
        """Tool 调用拦截钩子"""
        return tool_args

    async def on_tool_error(self, context: MiddlewareContext, tool_name: str, error: Exception) -> Optional[str]:
        """Tool 错误处理钩子，返回 fallback 内容或 None"""
        return None


class MiddlewareContext:
    """中间件上下文，贯穿整个请求生命周期"""
    session_id: str
    trace_id: str
    messages: list  # 当前对话历史
    token_usage: TokenUsage  # 累计 token 使用
    metadata: dict  # 可扩展元数据


class MiddlewarePipeline:
    """中间件管道，按顺序执行"""

    def __init__(self, middlewares: list[AgentMiddleware]):
        self._middlewares = middlewares

    async def execute(self, context: MiddlewareContext, agent_fn: Callable) -> OrchestratorOutput:
        for mw in self._middlewares:
            await mw.before_agent(context)
        result = await agent_fn(context)
        for mw in reversed(self._middlewares):
            result = await mw.after_agent(context, result)
        return result
```

### Decision 2: 记忆子系统基于 Redis 持久化，而非文件系统

**选择**: 使用 Redis Hash 存储记忆数据，LLM 异步提取和更新

**理由**: deer-flow 使用文件系统（`memory.json`）存储记忆，适合单机部署。我们的架构已依赖 Redis 作为核心基础设施（事件队列、会话状态），使用 Redis 可以：
1. 天然支持多实例部署
2. 复用现有连接池
3. 利用 Redis TTL 自动过期陈旧记忆

**替代方案**:
- 文件系统存储（deer-flow 方案）→ 不支持多实例，需要文件锁
- PostgreSQL 存储 → 引入额外依赖，当前未使用关系型数据库

**数据结构**:

```
memory:{user_id}:profile    → Hash { work_context, personal_context, top_of_mind }
memory:{user_id}:facts      → Sorted Set { score=timestamp, member=fact_json }
memory:{user_id}:updated_at → String (ISO timestamp)
```

### Decision 3: 渐进式 Skill 加载采用"摘要 + 按需全量"两阶段模式

**选择**: 启动时仅注入 Skill 名称和一句话描述列表，Agent 需要时通过 `search_skills` 工具获取完整 Skill 定义

**理由**: 参考 deer-flow 的 `deferred_tool_filter_middleware.py`，Skill 定义（含完整 SKILL.md 内容）可能占用大量 token。两阶段加载可以将初始 prompt 中的 Skill 信息从数千 token 压缩到几百 token。

**替代方案**:
- 全量注入（现状）→ Skill 增多后 token 浪费严重
- 完全不注入 → Agent 不知道有哪些 Skill 可用，无法主动调用

**实现方式**:
- 阶段 1（system prompt）: 注入 `Available skills: baidu-search (百度搜索), ai-ppt-generator (PPT生成), ...`
- 阶段 2（tool 调用）: Agent 调用 `search_skills(query)` 获取匹配 Skill 的完整定义，注入后续上下文

### Decision 4: 首批 Middleware 实现优先级

**选择**: 首批实现 5 个核心 middleware，按执行顺序排列：

1. `TokenUsageMiddleware` — token 用量监控和日志记录
2. `LoopDetectionMiddleware` — 重复 tool call 检测和强制终止（P0 安全）
3. `ToolErrorHandlingMiddleware` — tool 异常转为错误消息，防止 Agent 崩溃
4. `MemoryMiddleware` — 会话结束后异步更新记忆
5. `SummarizationMiddleware` — 长对话摘要压缩，控制 context window

**理由**: 参考 deer-flow 的 13 层 middleware，选取对稳定性和效率影响最大的 5 个。其余（clarification、todo、title、uploads 等）可在后续迭代中按需添加。

## Risks / Trade-offs

**[Risk] Middleware 管道增加请求延迟** → 每个 middleware 的 before/after 钩子应保持轻量（< 5ms），重操作（如记忆更新）异步执行，不阻塞主流程

**[Risk] 循环检测误判** → 采用 deer-flow 的滑动窗口 + hash 方案，warn_threshold=3 给 Agent 自我纠正机会，hard_limit=5 才强制终止。参数可通过配置调整

**[Risk] 记忆数据膨胀** → Redis Sorted Set 的 facts 设置上限（默认 100 条），超出时按时间戳淘汰最旧记录。profile 摘要通过 LLM 压缩，不会无限增长

**[Risk] 渐进式 Skill 加载增加一次 LLM 调用** → 仅在 Agent 判断需要 Skill 时才触发 search_skills，大多数简单查询不会触发。相比全量注入节省的 token，额外一次调用的成本可以接受

**[Trade-off] Middleware 基类不兼容 LangGraph** → 如果未来迁移到 LangGraph，middleware 需要重写。但当前选择保持架构一致性更重要

## Migration Plan

**Phase 1 — 基础设施（无破坏性变更）**
1. 新增 `src/middleware/` 目录，实现 base + pipeline + 5 个 middleware
2. 新增 `src/memory/` 目录，实现 storage + updater + retriever
3. 新增配置类 `MiddlewareSettings`、`MemorySettings`

**Phase 2 — 集成（向后兼容）**
4. 改造 `run_orchestrator()` 入口，包裹 middleware pipeline
5. 改造 `SkillRegistry`，实现两阶段加载
6. 新增 `search_skills` 和 `recall_memory` 工具注册到 Orchestrator
7. 新增 streaming 事件类型

**Phase 3 — 前端适配**
8. 前端 MessageHandler 处理新事件类型（可选，不影响核心功能）

**回滚策略**: middleware pipeline 通过配置开关控制（`middleware.enabled=true`），关闭后回退到直接调用 `run_orchestrator()`。记忆系统同理（`memory.enabled=true`）。

## Open Questions

- 记忆更新的 LLM 模型选择：使用 `fast` 模型（低成本）还是 `planning` 模型（高质量）？建议先用 `fast`，后续根据记忆质量调整
- SummarizationMiddleware 的触发阈值：对话超过多少 token 时触发摘要压缩？建议参考 deer-flow 的策略，按 context window 的 70% 触发
