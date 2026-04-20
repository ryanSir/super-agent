# Super-Agent 产线安全性分析

## 实际激活的 pydantic-deep 模块

根据 `agent_factory.py:101-146` 的调用参数，产线环境实际走到的代码路径：

| ✅ 激活 | | ❌ 未激活（参数关闭） | |
|---|---|---|---|
| `agent.py` | 工厂函数 | `toolsets/memory.py` | (include_memory=False) |
| `deps.py` | DI 容器 | `toolsets/checkpointing.py` | (include_checkpoints=False) |
| `hooks.py` | 循环检测+审计 | `toolsets/teams.py` | (include_teams=False) |
| `skills/toolset` | 技能系统 | `processors/patch.py` | (patch_tool_calls=False) |
| `skills/directory` | 技能发现 | `toolsets/context.py` | (无 context_files) |
| `plan/toolset` | 规划子代理 | `styles.py` | (无 output_style) |
| `eviction.py` | 大输出驱逐 | | |
| `history_archive` | 历史搜索 | | |
| `subagents.py` | 内置研究子代理 | | |
| `prompts.py` | 基础提示词 | | |

**外部依赖（激活）：**
```
├─ pydantic-ai-summarization → ContextManagerCapability
├─ pydantic-ai-shields       → CostTracking + ToolGuard
├─ pydantic-ai-todo          → TodoToolset
├─ subagents-pydantic-ai     → SubagentToolset
└─ pydantic-ai-backends      → StateBackend（纯内存）
```

---

## 逐模块产线风险评估

### 1. agent.py — 工厂函数 🟢 安全

**你的调用方式：**
```python
agent = create_deep_agent(
    model=get_model(model_alias),
    instructions=instructions,
    hooks=hooks,
    capabilities=capabilities,
    include_todo=True,
    include_subagents=True,
    include_filesystem=False,    # ← 关闭了文件系统
    include_skills=True,
    include_memory=False,        # ← 关闭了记忆
    include_checkpoints=False,   # ← 关闭了检查点
    web_search=False,
    web_fetch=False,
    thinking=False,
    context_manager=True,
    tools=[t for group in plan.resources.agent_tools.values() for t in group],
    toolsets=mcp_toolsets,
    patch_tool_calls=False,
    subagents=sub_agent_configs,
)
```

**风险分析：**
- **Bug #1**（工具注册丢失元数据）→ 不影响你。你传的 `tools` 是 `base_tools.py` 返回的裸函数（Callable），不是 Tool 对象，走的是 `agent.tool(tool)` 分支（line 963），不会丢失元数据
- **Bug #2**（私有属性注入）→ 低风险。`_context_middleware` 和 `_task_manager` 被设置了，但你的代码没有直接读取它们。只有 pydantic-deep CLI 的 `/compact` 命令会用到，你不用 CLI
- 工厂函数本身是纯组装逻辑，无状态，安全

---

### 2. deps.py — DeepAgentDeps + StateBackend 🟡 注意

**你的调用方式：**
```python
deps = create_default_deps(backend=StateBackend())
```

**风险分析：**
- **Bug #5**（访问 `backend._files` 私有属性）→ 会触发。`create_default_deps()` 创建 `DeepAgentDeps(backend=StateBackend())`，`__post_init__` 会执行 `object.__setattr__(self, "files", self.backend._files)`
- 但实际影响低：你没有直接操作 `deps.files`，StateBackend 是 pydantic-ai-backends 的稳定组件，`_files` 短期内不会改
- **真正的风险**：StateBackend 是纯内存的，进程重启数据全丢。如果你的 Agent 运行中途崩溃，所有 eviction 的文件、skill 缓存都丢失。但这对你的场景（单次请求-响应）是可接受的

---

### 3. hooks.py — HooksCapability 🟢 安全

**你的调用方式：**
```python
hooks = [
    Hook(event=HookEvent.PRE_TOOL_USE,         handler=detect_loop),
    Hook(event=HookEvent.BEFORE_RUN,           handler=reset_on_run),
    Hook(event=HookEvent.PRE_TOOL_USE,         handler=log_call),
    Hook(event=HookEvent.POST_TOOL_USE,        handler=log_result),
    Hook(event=HookEvent.POST_TOOL_USE_FAILURE, handler=log_failure),
]
```

**风险分析：**
- 你只用了 handler 模式（Python 函数），没用 command 模式（shell 命令）
- **Bug #10**（`asyncio.to_thread` 假设同步 execute）→ 不影响你，command hook 未使用
- **Bug #11**（后台 task 未追踪）→ 不影响你，所有 hook 都是 `background=False`（默认值）
- 你的 handler 都是简单的 dict 操作 + logging，不会抛异常
- `detect_loop` 的闭包状态（`call_hashes`/`hash_counts`）在 `reset_on_run` 中正确重置
- 安全

---

### 4. eviction.py — EvictionProcessor 🟡 注意

**激活方式：** `create_deep_agent()` 默认 `eviction_token_limit=20_000`，你没覆盖

**风险分析：**
- **Bug #7**（`_evicted_ids` 并发不安全）→ 需要评估。你的 `_run_agent()` 是 `async def`，在 FastAPI 的 asyncio 事件循环中运行。如果同一个 agent 实例被多个请求共享，`_evicted_ids` 会跨请求累积
- 但你的实际模式是安全的：`create_orchestrator_agent()` 每次请求都创建新的 agent 实例 → 新的 `EvictionProcessor` → 新的 `_evicted_ids`。不存在共享问题
- `backend.write()` 写入 StateBackend（内存），不涉及文件 I/O，不会阻塞
- 安全，但 `_evicted_ids` 会随对话轮次增长，长对话场景下内存微增（可忽略）

---

### 5. skills/ — SkillsToolset 🟡 注意

**你的调用方式：**
```python
skill_directories=[{"path": settings.skill_dir, "recursive": True}]
```

**风险分析：**
- **Bug #13**（默认 `./skills` 相对路径）→ 不影响你，你显式传了 `settings.skill_dir`
- 技能发现在 `__init__` 时同步执行（扫描目录、解析 `SKILL.md`），如果 skill 目录下文件很多，会阻塞 agent 创建
- **潜在问题**：每次请求都 `create_deep_agent()` → 每次都重新扫描 skill 目录。如果 skill 目录有 50+ 个 skill，每次请求多花 100-200ms
- **建议**：考虑缓存 `SkillsToolset` 实例或预加载 skill 列表

---

### 6. plan/toolset.py — 规划子代理 🟡 注意

**激活方式：** `include_plan` 默认 `True`，你没关闭

**风险分析：**
- planner 子代理会被注册到 subagents 列表中，LLM 可能会调用它
- planner 内部会创建一个新的 `create_deep_agent()`（递归），但关闭了大部分功能
- **潜在问题**：如果 LLM 误判调用 planner，会额外消耗一次 LLM 调用 + token
- **建议**：如果你的场景不需要 plan mode，显式 `include_plan=False` 节省 token

---

### 7. history_archive.py — 历史搜索 🟢 安全（但无用）

**激活方式：** `include_history_archive` 默认 `True`，`context_manager=True`

**风险分析：**
- **Bug #12**（`except Exception: pass`）→ 影响低，最坏情况是搜索返回空结果
- 但可能无用：`messages.json` 路径解析依赖 `backend.root_dir`，StateBackend 没有 `root_dir` 属性，会 fallback 到 `os.path.join(os.getcwd(), ".pydantic-deep/messages.json")`。如果进程工作目录没有写权限，历史搜索永远返回空
- **建议**：如果不需要，`include_history_archive=False`

---

### 8. subagents.py — 内置研究子代理 🟢 安全

**激活方式：** `include_builtin_subagents` 默认 `True`

**风险分析：**
- 只是注册了一个 "research" 子代理配置，不会自动执行
- 子代理创建时关闭了 `thinking`/`cost_tracking`/`context_manager`，token 消耗可控
- 安全

---

### 9. EventPublishingCapability（你的自定义） 🟡 注意

**风险分析：**
- `_reported_tool_ids` 是实例级 set，与 EvictionProcessor 同样的并发模式。但你每次请求创建新实例，安全
- `wrap_tool_execute` 内部 `import langfuse_tracer` → 如果 Langfuse 不可用，`trace_span` 需要优雅降级
- `after_model_request` 通过 `hasattr(response, "parts")` 做了防御性检查，安全
- **唯一风险**：`publish_fn` 如果抛异常，被 `except Exception` 捕获并 log warning，不会中断 agent 运行。安全

---

### 10. rest_api.py — Agent 运行入口 🔴 有风险

**风险分析：**

```python
# line 275-303
from pydantic_ai.models.anthropic import AnthropicModelSettings
from anthropic.types.beta import BetaThinkingConfigEnabledParam
```

- **`BetaThinkingConfigEnabledParam`** — 这是 Anthropic SDK 的 Beta API。beta 命名空间的类型随时可能改名或移除。Anthropic SDK 升级时这里会断
- **line 284-298**：DIRECT 和非 DIRECT 模式的 `model_settings` 代码完全相同（注释掉的才是区别），说明这里有未完成的逻辑
- **line 303**：`except Exception: pass` 吞掉了所有异常，如果 `AnthropicModelSettings` 导入失败，agent 会以无 thinking 模式运行，但不会报错。这是静默降级，产线上可能难以排查性能问题
- **line 319**：`if "run" in dir()` 检查变量是否存在 — 这是 Python 反模式，应该用 `try/except NameError` 或提前声明 `run = None`

---

## 产线风险总结

### 🔴 高风险（建议修复后上线）

**1. `rest_api.py:275-303` — `BetaThinkingConfigEnabledParam` 是 Beta API**
- Anthropic SDK 升级可能直接断裂
- **修复**：锁定 anthropic SDK 版本，或改用稳定的 thinking 配置方式

**2. `rest_api.py:303` — `except Exception: pass` 静默吞掉导入错误**
- 产线上 thinking 配置失败无任何告警
- **修复**：至少 `logger.warning`

---

### 🟡 中风险（可以上线，但建议优化）

**3. `skills/` — 每次请求重新扫描 skill 目录**
- 50+ skill 时每次请求多 100-200ms
- **优化**：缓存 `SkillsToolset` 或预加载

**4. `include_plan=True`（默认）— 注册了不需要的 planner 子代理**
- LLM 可能误调用，浪费 token
- **优化**：显式 `include_plan=False`

**5. `include_history_archive=True`（默认）— 历史搜索可能无法工作**
- StateBackend 无 `root_dir`，`messages.json` 路径可能无写权限
- **优化**：显式 `include_history_archive=False`，或指定有效路径

**6. `deps.py` — 访问 `StateBackend._files` 私有属性**
- pydantic-ai-backends 升级可能断裂
- **缓解**：锁定版本

---

### 🟢 安全（可直接上线）

| # | 模块 | 原因 |
|---|---|---|
| 7 | `hooks.py` | 只用 handler 模式，无 shell 命令风险 |
| 8 | `eviction.py` | 每次请求新实例，无并发问题 |
| 9 | `EventPublishingCapability` | 异常安全，不中断主流程 |
| 10 | `patch.py` | 已关闭（patch_tool_calls=False） |
| 11 | `checkpointing.py` |


| 11 | `checkpointing.py` | 已关闭（include_checkpoints=False） |
| 12 | `memory.py` | 已关闭（include_memory=False） |
| 13 | `teams.py` | 已关闭（include_teams=False） |

---

## 产线上线前建议的 4 个改动

### 1. 锁定关键依赖版本（5 分钟）

```toml
# pyproject.toml
pydantic-deep = "==0.3.3"          # 不用 ^0.3
pydantic-ai-slim = "==1.83.0"
anthropic = "==0.52.0"             # 锁定，避免 Beta API 变动
```

### 2. 修复 rest_api.py 的 Beta API 风险（10 分钟）

```python
# 替换 BetaThinkingConfigEnabledParam
# 改用 pydantic-ai 的稳定 API
iter_kwargs["model_settings"] = AnthropicModelSettings(
    anthropic_thinking={"type": "enabled", "budget_tokens": budget},
    max_tokens=max_tokens,
)
```

### 3. 关闭不需要的默认功能（2 分钟）

```python
agent = create_deep_agent(
    ...
    include_plan=False,              # 你有自己的 ReasoningEngine
    include_history_archive=False,   # StateBackend 下无法正常工作
    include_builtin_subagents=False, # 你有自己的 sub_agent_configs
)
```

### 4. 给 except Exception: pass 加日志（5 分钟）

```python
# rest_api.py:303
except Exception as e:
    logger.warning(f"Thinking 配置失败，使用默认设置 | error={e}")
```

---

做完这 4 个改动，pydantic-deep 相关的代码路径在产线上是稳定的。核心风险不在框架本身，而在你对 Anthropic Beta API 的直接依赖。