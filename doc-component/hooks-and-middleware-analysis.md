# Hooks & Middleware 深入分析

## 一、概念辨析：Hooks vs Middleware vs Capabilities

在 pydantic-deep 框架演进中，这三个概念有明确的层次关系：

| 概念 | 定位 | 当前状态 |
|------|------|----------|
| **Middleware** | 旧版拦截层（`AgentMiddleware`、`MiddlewareAgent`） | **已废弃**，被 Capabilities API 替代 |
| **Capabilities** | pydantic-ai 原生能力单元（`AbstractCapability`） | **当前标准**，middleware 的继任者 |
| **Hooks** | Capabilities 的一种具体实现（`HooksCapability`） | **活跃使用**，Claude Code 风格的事件钩子 |

关系链：`Hooks ⊂ Capabilities ⊃ (旧 Middleware 的所有能力)`

---

## 二、pydantic-deep 框架层：Capabilities API

### 2.1 AbstractCapability 完整生命周期

Capabilities 是 pydantic-ai 原生支持的可组合行为单元，通过 `capabilities=[...]` 参数注册到 Agent。

```
Agent 构建阶段（一次性）
├── get_instructions()          → 注入 system prompt 片段
├── get_model_settings()        → 合并模型配置
├── get_toolset()               → 注册工具集
└── get_builtin_tools()         → 注册内置工具（web search 等）

每次 Run 阶段
├── for_run(ctx)                → 创建隔离实例（状态隔离）
├── get_wrapper_toolset(toolset)→ 包装组合工具集
├── prepare_tools(ctx, tool_defs)→ 过滤/修改可见工具定义
│
├── Run 生命周期
│   ├── before_run(ctx)                              [观察]
│   ├── wrap_run(ctx, handler)                       [包装整个 run]
│   ├── after_run(ctx, result)                       [可修改结果]
│   └── on_run_error(ctx, error)                     [错误恢复]
│
├── Model Request 生命周期（每次 LLM 调用）
│   ├── before_model_request(ctx, request_context)   [修改请求]
│   ├── wrap_model_request(ctx, request_context, handler) [包装]
│   ├── after_model_request(ctx, request_context, response) [修改响应]
│   └── on_model_request_error(ctx, request_context, error) [错误处理]
│
└── Tool 生命周期（每次工具调用）
    ├── Validate 阶段
    │   ├── before_tool_validate(ctx, call, tool_def, args)  [修改原始参数]
    │   ├── wrap_tool_validate(ctx, call, tool_def, args, handler)
    │   ├── after_tool_validate(ctx, call, tool_def, args)   [修改验证后参数]
    │   └── on_tool_validate_error(ctx, call, tool_def, args, error)
    │
    └── Execute 阶段
        ├── before_tool_execute(ctx, call, tool_def, args)   [修改参数/拦截]
        ├── wrap_tool_execute(ctx, call, tool_def, args, handler)
        ├── after_tool_execute(ctx, call, tool_def, args, result) [修改结果]
        └── on_tool_execute_error(ctx, call, tool_def, args, error)
```

### 2.2 Capability 注册方式

```python
# 方式一：显式传入 capabilities 列表
agent = create_deep_agent(
    capabilities=[
        CostTracking(budget_usd=10.0),
        HooksCapability(hooks=[...]),
        MyCustomCapability(),
    ],
)

# 方式二：通过 feature flags 自动创建（create_deep_agent 内部处理）
agent = create_deep_agent(
    cost_tracking=True,          # → CostTracking capability
    hooks=[...],                 # → HooksCapability
    context_manager=True,        # → ContextManagerCapability
    include_checkpoints=True,    # → CheckpointMiddleware (已迁移为 Capability)
)
```

### 2.3 框架内置 Capabilities

| Capability | 启用方式 | 功能 |
|---|---|---|
| `CostTracking` | `cost_tracking=True` | Token/USD 成本追踪（来自 pydantic_ai_shields） |
| `HooksCapability` | `hooks=[...]` | Claude Code 风格生命周期钩子 |
| `CheckpointMiddleware` | `include_checkpoints=True` | 对话检查点自动保存 |
| `ContextManagerCapability` | `context_manager=True` | Token 追踪 + 自动压缩（来自 pydantic_ai_summarization） |
| `WebSearch` | `web_search=True` | 内置 Web 搜索 |
| `WebFetch` | `web_fetch=True` | 内置 URL 抓取 |

### 2.4 自定义 Capability 示例

```python
# 安全门控 Capability — 比 Hook 更强大，可以访问完整的 tool_def 和 ctx
@dataclass
class SafetyGate(AbstractCapability):
    blocked_patterns: list[str]

    async def before_tool_execute(self, ctx, *, call, tool_def, args):
        if call.tool_name == "execute":
            command = args.get("command", "")
            for pattern in self.blocked_patterns:
                if pattern in command:
                    raise ModelRetry(f"Blocked: '{pattern}'")
        return args

# 请求计数器 — 演示 for_run 状态隔离
@dataclass
class RequestCounter(AbstractCapability):
    count: int = 0

    async def for_run(self, ctx):
        return RequestCounter(count=0)  # 每次 run 独立计数

    async def before_model_request(self, ctx, request_context):
        self.count += 1
        return request_context
```

---

## 三、pydantic-deep 框架层：Hooks 系统

### 3.1 Hooks 本质

Hooks 是 `HooksCapability`（一个 `AbstractCapability` 子类）的用户接口。它将 Capability 的细粒度生命周期方法映射为更简单的事件模型：

```
AbstractCapability 方法          →  HookEvent 映射
─────────────────────────────────────────────────
before_tool_execute()           →  PRE_TOOL_USE
after_tool_execute()            →  POST_TOOL_USE
on_tool_execute_error()         →  POST_TOOL_USE_FAILURE
before_run()                    →  BEFORE_RUN
after_run()                     →  AFTER_RUN
on_run_error()                  →  RUN_ERROR
before_model_request()          →  BEFORE_MODEL_REQUEST
after_model_request()           →  AFTER_MODEL_REQUEST
```

### 3.2 Hook 事件类型

**工具事件：**
- `PRE_TOOL_USE` — 工具执行前（可拒绝、可修改参数）
- `POST_TOOL_USE` — 工具执行成功后（可修改结果）
- `POST_TOOL_USE_FAILURE` — 工具执行失败后（仅观察）

**Run 事件：**
- `BEFORE_RUN` — agent.run() 开始（setup、会话追踪）
- `AFTER_RUN` — agent.run() 结束（cleanup、审计）
- `RUN_ERROR` — agent.run() 失败（错误追踪、告警）

**Model Request 事件：**
- `BEFORE_MODEL_REQUEST` — 每次 LLM 调用前（限流、日志）
- `AFTER_MODEL_REQUEST` — 每次 LLM 响应后（token 追踪、日志）

### 3.3 Hook 两种实现形式

```python
# 形式一：Python Handler（推荐，进程内直接调用）
async def safety_gate(hook_input: HookInput) -> HookResult:
    if "rm -rf" in str(hook_input.tool_input):
        return HookResult(allow=False, reason="Dangerous command blocked")
    return HookResult(allow=True)

Hook(event=HookEvent.PRE_TOOL_USE, handler=safety_gate, matcher="execute")

# 形式二：Command Hook（Shell 命令，通过 SandboxProtocol 执行）
# stdin 接收 HookInput JSON，exit 0=允许，exit 2=拒绝
Hook(
    event=HookEvent.PRE_TOOL_USE,
    command="python scripts/security_check.py",
    matcher="execute",
    timeout=30,
)
```

### 3.4 HookInput / HookResult 数据结构

```python
# 传入 Hook 的数据
class HookInput:
    event: str              # 事件名
    tool_name: str          # 工具名
    tool_input: dict        # 工具参数
    tool_result: str | None # 工具输出（仅 POST 事件）
    tool_error: str | None  # 错误信息（仅 POST_TOOL_USE_FAILURE）

# Hook 返回的决策
class HookResult:
    allow: bool = True          # 是否允许执行
    reason: str = ""            # 拒绝原因
    modified_args: dict = None  # 修改后的参数（PRE 事件）
    modified_result: str = None # 修改后的结果（POST 事件）
```

### 3.5 执行顺序

- **PRE_TOOL_USE**：顺序执行，first deny wins，参数修改累积传递
- **POST_TOOL_USE**：顺序执行，结果修改链式传递，background hooks 并行不阻塞
- **非工具事件**：matcher 忽略，所有 hooks 都触发

### 3.6 高级特性

```python
# Matcher — 正则匹配工具名
Hook(event=HookEvent.PRE_TOOL_USE, handler=h, matcher="execute|write_file")

# Background — 异步不阻塞
Hook(event=HookEvent.POST_TOOL_USE, handler=analytics, background=True)

# 修改参数（PRE 事件）
async def normalize(inp: HookInput) -> HookResult:
    args = dict(inp.tool_input)
    args["path"] = args["path"].replace("../", "")
    return HookResult(allow=True, modified_args=args)

# 修改结果（POST 事件）
async def redact(inp: HookInput) -> HookResult:
    return HookResult(modified_result=inp.tool_result.replace("SECRET", "***"))
```

---

## 四、Hooks vs Capabilities 对比决策

| 维度 | Hooks | Capabilities |
|------|-------|-------------|
| **抽象层级** | 高层（事件 + handler） | 底层（完整生命周期方法） |
| **适用场景** | 审计、安全门控、事件推送、简单拦截 | 复杂行为注入、工具集包装、状态隔离、错误恢复 |
| **访问粒度** | `HookInput`（tool_name, tool_input, tool_result） | 完整 `RunContext`、`ToolCallPart`、`ToolDefinition` |
| **状态管理** | 闭包变量 | `for_run()` 实例隔离 |
| **工具注入** | 不支持 | `get_toolset()` / `get_builtin_tools()` |
| **Prompt 注入** | 不支持 | `get_instructions()` |
| **Validate 阶段** | 不支持 | `before/after/wrap_tool_validate` |
| **Wrap 模式** | 不支持 | `wrap_run` / `wrap_model_request` / `wrap_tool_execute` |
| **外部集成** | Command Hook（Shell 命令） | 仅 Python |
| **配置复杂度** | 低（声明式） | 中（需要子类化） |

**选择原则：**
- 简单的"观察/拦截/修改"逻辑 → 用 Hooks
- 需要注入工具、修改 prompt、包装执行流、状态隔离 → 用 Capabilities
- 需要 Shell 命令集成（CI/CD、外部脚本） → 用 Command Hooks

---

## 五、当前系统实现分析

### 5.1 Hooks 层（pydantic-deep 框架级）

文件：`src_deepagent/orchestrator/hooks.py`

当前实现了 4 类 Hooks，通过工厂函数 `create_hooks()` 统一创建：

```
create_hooks(publish_fn)
├── create_event_push_hooks()      # 事件推送（当前禁用，避免与 rest_api 重复）
│   ├── PRE_TOOL_USE  → on_tool_call()     [background]
│   ├── POST_TOOL_USE → on_tool_result()   [background]
│   └── POST_TOOL_USE_FAILURE → on_tool_failure() [background]
│
├── create_loop_detection_hooks()  # 循环检测（活跃）
│   ├── PRE_TOOL_USE  → detect_loop()      [滑动窗口 + MD5 指纹]
│   └── BEFORE_RUN    → reset_on_run()     [重置状态]
│
├── create_audit_hooks()           # 安全审计（活跃）
│   ├── PRE_TOOL_USE  → log_call()         [记录工具名+参数]
│   ├── POST_TOOL_USE → log_result()       [记录耗时+结果]
│   └── POST_TOOL_USE_FAILURE → log_failure() [记录错误]
│
└── create_token_tracker_hooks()   # Token 追踪（占位，未实现）
    └── AFTER_MODEL_REQUEST → track_tokens() [no-op]
```

注册路径：`agent_factory.py:68` → `create_hooks(publish_fn)` → `create_deep_agent(hooks=hooks)`

### 5.2 Capabilities 层（pydantic-deep 框架级）

通过 `create_deep_agent()` 的 feature flags 隐式启用：

```python
# agent_factory.py:77-115
agent = create_deep_agent(
    hooks=hooks,                    # → HooksCapability（自动包装）
    context_manager=True,           # → ContextManagerCapability（token 追踪 + 自动压缩）
    context_manager_max_tokens=200_000,
    cost_tracking=True,             # → CostTracking（成本追踪）
    include_skills=True,            # → SkillsToolset（Skill 工具集注入）
    include_todo=True,              # → TodoCapability（任务管理）
    include_subagents=True,         # → SubAgentCapability（子 Agent 委派）
)
```

当前系统实际使用的 Capabilities 栈：

| Capability | 来源 | 功能 |
|---|---|---|
| `HooksCapability` | `hooks=[...]` | 包装上述 4 类 Hooks |
| `ContextManagerCapability` | `context_manager=True` | 200K token 上限 + 自动压缩 |
| `CostTracking` | `cost_tracking=True` | Token/USD 成本追踪 |
| `SkillsToolset` | `include_skills=True` | Skill 目录扫描 + 工具注册 |
| `TodoCapability` | `include_todo=True` | 任务管理工具 |
| `SubAgentCapability` | `include_subagents=True` | 子 Agent 委派 |

### 5.3 FastAPI Middleware 层（应用级）

文件：`src_deepagent/main.py`

```python
# 唯一的 FastAPI 中间件：CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.4 应用生命周期（Lifespan）

文件：`src_deepagent/main.py:26-60`

```
Startup
├── configure_litellm()           # LLM 路由配置
├── configure_langfuse()          # 分布式追踪
├── _init_redis()                 # Redis 连接（降级容忍）
├── rest_api.init_workers()       # Worker 初始化
├── rest_api.configure()          # 网关配置
└── rest_api.startup()            # MCP 连接 + 定期刷新

Shutdown
├── rest_api.shutdown()           # MCP 刷新任务取消
├── langfuse_shutdown()           # 追踪关闭
└── redis_client.close()          # Redis 关闭
```

### 5.5 其他类 Hook 模式

| 模式 | 位置 | 机制 |
|------|------|------|
| 事件发布回调 | `base_tools.py` | `ContextVar[publish_fn]` 注入，工具执行后推送事件 |
| Langfuse 追踪 | `langfuse_tracer.py` | `@traced()` 装饰器 + `trace_span()` 上下文管理器 |
| 会话状态机 | `session_manager.py` | 状态转换校验（CREATED→PLANNING→EXECUTING→COMPLETED） |
| MCP 刷新循环 | `reasoning_engine.py` | `_refresh_loop()` 定期刷新 MCP 工具可用性 |

---

## 六、架构评估

### 6.1 当前做得好的

1. **Hooks 职责清晰** — 4 类 Hook 各司其职（事件推送、循环检测、审计、token 追踪），工厂函数统一组装
2. **循环检测设计精巧** — 滑动窗口 + MD5 指纹 + 分级响应（warn → hard reject），`BEFORE_RUN` 重置避免跨 run 污染
3. **Capabilities 合理利用** — 通过 feature flags 启用框架内置能力，没有重复造轮子
4. **降级容忍** — pydantic-deep 不可用时有 fallback agent，Redis 连接失败不阻塞启动

### 6.2 待改进项

1. **事件推送 Hooks 被禁用** — `create_event_push_hooks()` 全部注释，事件推送仍在 `rest_api._run_agent()` 中硬编码。应迁移到 Hook 层，实现关注点分离
2. **Token Tracker 是空壳** — `track_tokens()` 是 no-op，应对接 `CostTracking` capability 或 Langfuse
3. **审计 Hook 用 tool_name 做 key** — `call_start_times[inp.tool_name]` 在并发调用同名工具时会覆盖，应改用唯一 call ID
4. **缺少自定义 Capability** — 所有自定义逻辑都走 Hooks，没有利用 Capability 的高级能力（工具注入、prompt 注入、wrap 模式、状态隔离）
5. **FastAPI 中间件单薄** — 只有 CORS，缺少请求级中间件（认证、限流、请求 ID 注入、错误标准化）
6. **publish_fn 注入方式** — 通过 `ContextVar` 在 `base_tools.py` 注入，与 Hook 的 `publish_fn` 参数形成两条并行路径，职责不清

### 6.3 Hooks vs Capabilities 使用建议

```
当前用 Hooks 合适的：
  ✓ 循环检测（简单拦截逻辑）
  ✓ 安全审计（观察 + 日志）
  ✓ 事件推送（观察 + 异步推送）

应考虑升级为 Capability 的：
  → Token 追踪 — 需要 for_run() 状态隔离 + 与 CostTracking 联动
  → 权限控制 — 需要 before_tool_execute + ModelRetry 异常
  → 动态工具过滤 — 需要 prepare_tools() 按角色/模式过滤可见工具
  → Prompt 注入 — 需要 get_instructions() 动态注入上下文
```

---

## 七、企业级场景：Hooks vs Capabilities 职责划分

### 7.1 Hooks 层（事件驱动，轻量拦截）

适合**横切关注点**，逻辑简单、不需要改变执行流程：

| 能力 | Hook 事件 | 说明 |
|------|-----------|------|
| 安全审计日志 | PRE/POST_TOOL_USE | 记录谁调了什么、参数、耗时、结果 |
| 循环检测 | PRE_TOOL_USE + BEFORE_RUN | 滑动窗口 + 指纹去重 |
| 敏感信息脱敏 | POST_TOOL_USE | 结果中的密钥、PII 替换为 `***` |
| 参数规范化 | PRE_TOOL_USE | 路径清理、注入默认值 |
| 危险操作拦截 | PRE_TOOL_USE | `rm -rf`、`DROP TABLE` 等黑名单 |
| 事件推送（SSE） | PRE/POST_TOOL_USE | 工具执行状态推到前端 |
| 错误告警 | RUN_ERROR | 发 webhook / Slack / 钉钉 |
| 请求计数 | BEFORE_MODEL_REQUEST | 简单的调用次数统计 |

共同特征：**观察、拦截、修改数据，不改变 Agent 的行为结构**。

### 7.2 Capabilities 层（行为注入，深度控制）

适合**需要改变 Agent 能力边界或执行流程**的场景：

| 能力 | 用到的方法 | 为什么 Hooks 做不了 |
|------|-----------|-------------------|
| 多租户权限控制 | `prepare_tools()` | 按租户/角色动态过滤可见工具集，Hooks 看不到工具列表 |
| 动态 Prompt 注入 | `get_instructions()` | 按会话上下文注入不同的 system prompt 片段 |
| Token 预算管控 | `wrap_model_request()` | 需要包装整个 LLM 调用，超预算时中断 run |
| 对话自动压缩 | `before_model_request()` + 状态 | 需要访问完整 message history + `for_run()` 状态隔离 |
| 工具执行超时/重试 | `wrap_tool_execute()` | 需要包装执行流，加 timeout/retry 逻辑 |
| 结果缓存 | `before/after_tool_execute()` + 状态 | 需要 `for_run()` 隔离缓存实例，避免跨 run 污染 |
| 自定义工具集注入 | `get_toolset()` | Hooks 完全没有注入工具的能力 |
| A/B 测试路由 | `get_model_settings()` | 按实验分组切换模型参数 |
| 合规审计（完整链路） | `wrap_run()` | 需要包装整个 run，记录输入→输出完整链路 |
| 参数 Schema 校验 | `before_tool_validate()` | Hooks 介入不了 validate 阶段 |

### 7.3 判断原则

```
问自己三个问题：

1. 需要注入工具或修改 Prompt 吗？     → Capability
2. 需要 wrap 执行流或状态隔离吗？      → Capability
3. 只是观察/拦截/修改数据流？          → Hook 就够了
```

### 7.4 当前系统建议调整

```
保持 Hook：
  ✓ 循环检测 — 简单拦截，滑动窗口 + 指纹
  ✓ 安全审计 — 观察 + 日志
  ✓ 事件推送 — 观察 + 异步推送
  ✓ 危险操作拦截 — PRE_TOOL_USE 黑名单
  ✓ 敏感信息脱敏 — POST_TOOL_USE 结果替换
  ✓ 错误告警 — RUN_ERROR 推送通知

升级为 Capability：
  → Token 追踪 — 对接 CostTracking，需要 wrap_model_request
  → 权限控制 — prepare_tools() 按角色过滤工具
  → 多租户隔离 — for_run() 隔离 + 动态 prompt 注入
  → 工具超时/重试 — wrap_tool_execute() 包装执行流
```

---

## 八、总结：三层拦截体系

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Middleware 层（HTTP 请求级）                      │
│  CORS / 认证 / 限流 / 请求ID / 错误标准化                  │
│  ↓                                                       │
│  FastAPI Lifespan（应用生命周期）                           │
│  Redis / LiteLLM / Langfuse / MCP / Workers 初始化        │
├─────────────────────────────────────────────────────────┤
│  pydantic-ai Capabilities 层（Agent 行为级）               │
│  CostTracking / ContextManager / Skills / SubAgent / Todo │
│  ↓                                                       │
│  自定义 Capability（高级行为注入）                          │
│  工具注入 / Prompt 注入 / Wrap 模式 / 状态隔离              │
├─────────────────────────────────────────────────────────┤
│  Hooks 层（事件级，HooksCapability 内部）                   │
│  事件推送 / 循环检测 / 安全审计 / Token 追踪                │
│  ↓                                                       │
│  Command Hooks（外部脚本集成）                             │
│  Shell 命令 / CI 脚本 / 安全扫描器                         │
└─────────────────────────────────────────────────────────┘
```

框架的设计意图很清晰：**Capabilities 是底层基础设施，Hooks 是面向用户的简化接口**。当前系统主要使用 Hooks + 内置 Capabilities，尚未充分利用自定义 Capability 的高级能力。随着系统复杂度增长（权限控制、动态工具过滤、多租户隔离），应逐步引入自定义 Capabilities。
