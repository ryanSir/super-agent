# Toolset 框架能力分析与复用决策

> pydantic-deep Toolset 体系深度分析 — 哪些复用、哪些不动、为什么

## 一、框架 Toolset 架构全景

```
AbstractToolset                          ← 抽象基类，定义完整生命周期
├── FunctionToolset                      ← 具体实现，@tool 装饰器注册
├── CombinedToolset                      ← 合并多个 toolset，冲突检测
├── WrapperToolset                       ← 装饰器模式基类
│   ├── FilteredToolset                  ← .filtered(fn) 按条件过滤
│   ├── PrefixedToolset                  ← .prefixed("db_") 加前缀
│   ├── RenamedToolset                   ← .renamed(map) 重命名
│   ├── ApprovalRequiredToolset          ← .approval_required(fn) 审批
│   ├── PreparedToolset                  ← .prepared(fn) 每步修改定义
│   │   ├── DeferredLoadingToolset       ← .defer_loading() 延迟加载
│   │   ├── SetMetadataToolset           ← .with_metadata() 注入元数据
│   │   └── IncludeReturnSchemasToolset  ← .include_return_schemas()
│   └── 自定义 Wrapper（如 ObservabilityToolset）
└── SkillsToolset(FunctionToolset)       ← 技能系统（已启用）
```

## 二、生命周期 Hook

框架提供四层 hook，当前项目仅通过 SkillsToolset 间接使用：

```
Agent.run() 开始
    │
    ▼
for_run(ctx)          ← 每次 run 创建隔离实例
    │
    ▼
__aenter__()          ← 资源初始化
    │
    ▼
┌─── 推理循环 ────────────────────────┐
│  for_run_step(ctx)  ← 每步状态转换   │
│       │                              │
│  get_tools(ctx)     ← 返回当前可用工具│
│       │                              │
│  call_tool(...)     ← 执行工具       │
└──────────────────────────────────────┘
    │
    ▼
__aexit__()           ← 资源清理
```

## 三、框架 Toolset vs 当前 Base Tools 实现

| 维度 | 当前实现 | 框架能力 |
|------|---------|---------|
| 注册方式 | `create_base_tools()` 返回闭包函数列表 | `FunctionToolset` + `@toolset.tool` 装饰器 |
| 组织形式 | 9 个函数平铺在一个大闭包里（分组 dict） | 按职责拆分为独立 Toolset |
| 依赖注入 | 闭包捕获 `workers` 字典 | `ctx.deps` 依赖注入 |
| 组合机制 | 手动列表推导合并 | `CombinedToolset` 自动合并 + 冲突检测 |
| 工具过滤 | `agents/factory.py` 手动排除 `plan` 组 | `.filtered(fn)` 声明式 |
| Prompt 注入 | `builder.py` 集中式 12 段 | 各 Toolset `get_instructions(ctx)` 分散 |
| 观测性 | `_wrap_with_tool_result` 逐函数包装 | `WrapperToolset.call_tool()` 统一拦截 |
| 生命周期 | 无 | `for_run` / `for_run_step` / `__aenter__` / `__aexit__` |

## 四、复用决策：不迁移 Base Tools 到 FunctionToolset

### 决策

保持当前方式（分组 dict + 闭包），不将 base tools 迁移到 `FunctionToolset` 装饰器模式。

### 核心原因：DeepAgentDeps 不支持自定义字段扩展

当前工具通过闭包捕获 `workers` 字典获取 Worker 实例。如果改成 `@toolset.tool` 装饰器，需要通过 `ctx.deps.workers` 获取。但框架的 `DeepAgentDeps` 是固定字段的 dataclass：

```python
# pydantic_deep/deps.py — 框架定义，不可修改
@dataclass
class DeepAgentDeps:
    backend: BackendProtocol
    files: dict[str, FileData]
    todos: list[Todo]
    subagents: dict[str, Any]
    uploads: dict[str, UploadedFile]
    ask_user: Any
    context_middleware: Any
    share_todos: bool
    # ← 没有 workers 字段
```

### 负面影响分析

**1. deps 扩展困难（严重程度：高）**

要把 `workers` 塞进 `ctx.deps`，三条路都有问题：

| 方案 | 问题 |
|------|------|
| 继承 `DeepAgentDeps` 加 `workers` 字段 | `create_deep_agent()` 内部硬编码 `deps_type=DeepAgentDeps`，子类不一定兼容 |
| 塞进 `deps.metadata` | hack，metadata 本意是存 session_id 等轻量数据 |
| 保持闭包 | 也就是不改 ← 最安全 |

**2. Sub-Agent deps 传递链断裂（严重程度：高）**

框架内部创建 Sub-Agent 时会 clone parent deps：

```python
# 框架内部
sub_deps = clone_deps(parent_deps)  # 只认识框架定义的字段
await subagent.run(description, deps=sub_deps)
```

闭包方式下，Sub-Agent 的工具函数天然能访问 workers（同一个闭包实例）。改成 `ctx.deps.workers` 后，框架的 `clone_deps` 不认识自定义字段，Sub-Agent 里的工具可能拿不到 workers。

**3. 工具函数签名变更（严重程度：中）**

9 个工具函数的 `RunContext[Any]` 要改成 `RunContext[DeepAgentDeps]`，所有调用方都要适配。

**4. 缓存策略变更（严重程度：低）**

当前 `_resolve_resources()` 缓存了 `create_base_tools(workers)` 的结果。改成模块级 FunctionToolset 后缓存逻辑需要重新设计。

**5. 测试复杂度增加（严重程度：低）**

闭包方式可以直接 `create_base_tools(mock_workers)` 单测。FunctionToolset 方式需要构造完整的 `DeepAgentDeps`。

### 等价性论证

`create_deep_agent(tools=[fn1, fn2, ...])` 内部会自动把函数列表包装成 `FunctionToolset`：

```python
# pydantic_ai Agent.__init__ 内部
if tools:
    toolset = FunctionToolset()
    for fn in tools:
        toolset.add_function(fn, ...)  # 自动包装
```

当前传闭包函数和用 `@toolset.tool` 注册，最终走的是同一条路。显式使用 FunctionToolset 只是代码组织方式的差异，不带来功能增益。

## 五、可以在组装层复用的框架能力

不改 `base_tools.py` 内部，在外层组装时可以利用框架 Wrapper：

### 1. ObservabilityToolset — 替代 `_wrap_with_tool_result`（P0）

当前 `_wrap_with_tool_result` 逐函数包装做 Langfuse span + SSE 推送。可以用 `WrapperToolset.call_tool()` 统一拦截：

```python
class ObservabilityToolset(WrapperToolset):
    async def call_tool(self, name, tool_args, ctx, tool):
        with trace_span(f"tool_{name}", as_type="tool"):
            result = await super().call_tool(name, tool_args, ctx, tool)
            await publish_tool_result(name, result)
            return result
```

一个 wrapper 替代 N 个 `_wrap_with_tool_result` 调用。

### 2. defer_loading() — MCP 工具渐进式加载（P1）

```python
mcp_toolset = FastMCPToolset(url).defer_loading()
# Agent prompt 里不出现这些工具描述
# Agent 可通过 tool_search 按需发现
```

对 MCP 工具特别有价值 — 可能有几十个，全量注入浪费 token。

### 3. filtered() — 声明式工具过滤（P2）

```python
sub_agent_toolset = combined_toolset.filtered(
    lambda ctx, tool_def: tool_def.name != "plan_and_decompose"
)
```

替代当前 `agents/factory.py` 手动排除 `plan` 组的逻辑。

### 4. CombinedToolset — 冲突检测（P2）

当前 base tools 和 MCP tools 如果同名会静默覆盖。框架自动检测并报错。随 FunctionToolset 拆分一起获得。

## 六、Hooks vs Toolset — 职责划分

当前项目有两套工具调用拦截机制，加上 `_wrap_with_tool_result` 共三套：

```
机制                        能力                          当前状态
──────────────────────     ──────────────────────        ──────────
_wrap_with_tool_result     完整 AOP（改入参/包装返回值）   正在使用（主力）
hooks.py Hook 系统          事件通知（只能 allow/deny）    部分使用（推送被注释）
Toolset.call_tool()        完整 AOP + 框架生命周期        未使用
```

正确的职责划分：

| 机制 | 适合做什么 | 不适合做什么 |
|------|----------|------------|
| Hooks | 循环检测（PRE_TOOL_USE, deny）、审计日志（记录）、Token 追踪 | 修改工具行为、包装返回值 |
| Toolset.call_tool() | Langfuse span 追踪、SSE 推送、错误格式化 | 简单的事件通知 |
| _wrap_with_tool_result | 应被 Toolset.call_tool() 替代 | — |

**Hooks 是观察者，Toolset 是参与者。** 两者互补，不冲突。

## 七、迁移路线图

```
Phase 0（已完成 — skill 重构）：
  ✓ create_base_tools() 返回分组 dict
  ✓ SkillsToolset 启用
  ✓ Sub-Agent 全量注入

Phase 1（后续 — 观测性统一）：
  → ObservabilityToolset 替代 _wrap_with_tool_result
  → 删除 hooks.py 中被注释的事件推送
  → base_tools.py 工具函数不再需要 _wrap 包装

Phase 2（后续 — 渐进式加载）：
  → MCP toolset 启用 defer_loading()
  → 减少 prompt token 开销

Phase 3（远期 — 完整 Toolset 化）：
  → 等框架 DeepAgentDeps 支持自定义字段扩展
  → 或等 pydantic-ai 核心提供更灵活的 deps 机制
  → 届时再将 base_tools.py 拆分为独立 FunctionToolset
```

## 八、什么时候值得完整迁移

当出现以下任一情况时重新评估：

- base tool 数量超过 20 个，一个文件放不下
- 不同工具需要不同的 `get_instructions()` prompt 注入
- 需要工具级别的 `for_run()` 状态隔离
- 需要工具级别的 `prepare()` 动态 schema 修改
- 框架 `DeepAgentDeps` 支持自定义字段扩展或提供 `metadata` 的类型安全替代方案

当前 9 个工具，这些场景都不存在。**保持闭包方式是当前最安全、最简单的选择。**
