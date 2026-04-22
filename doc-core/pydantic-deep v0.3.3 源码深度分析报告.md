# pydantic-deep v0.3.3 源码深度分析报告

▎ 技术选型参考 | 基于 pydantic-ai 1.83.0 | 8,424 行 / 33 模块
▎ 2026-04-17

---

## 1. 架构速览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│  create_deep_agent()  — 工厂函数 (agent.py, 1033行)   │
│  组装所有组件，返回 pydantic-ai Agent 实例              │
├─────────────────────────────────────────────────────┤
│  DeepAgentDeps  — DI 容器 (deps.py, 239行)            │
│  backend / files / todos / subagents / uploads       │
├──────────┬──────────┬───────────┬───────────────────┤
│ Toolsets │Capabilities│Processors│  动态指令          │
│ (工具集)  │ (生命周期)  │(消息管道) │ (系统提示词)       │
├──────────┼──────────┼───────────┼───────────────────┤
│ Skills   │ Hooks    │ Eviction  │ dynamic_          │
│ Memory   │ Checkpoint│ Patch    │ instructions()    │
│ Context  │ CostTrack│ History   │ todo/console/     │
│ Plan     │ Thinking │ Archive   │ subagent prompts  │
│ Teams    │ WebSearch│           │                   │
│ Checkpoint│ WebFetch│           │                   │
└──────────┴──────────┴───────────┴───────────────────┘
         ↓                ↓
   pydantic-ai Agent    pydantic-ai-backends
   (AbstractToolset)    (BackendProtocol/SandboxProtocol)
```

### 1.2 核心数据流

```
create_deep_agent(model, instructions, tools, toolsets, capabilities, ...)
  │
  ├─ 1. 解析 backend（默认 StateBackend）
  ├─ 2. 组装 all_toolsets[]
  │     ├─ TodoToolset（通过 _DepsTodoProxy 代理）
  │     ├─ ConsoleToolset（文件系统操作）
  │     ├─ SubagentToolset（task() 委派）
  │     ├─ SkillsToolset（渐进式加载）
  │     ├─ ContextToolset（AGENTS.md/SOUL.md 注入）
  │     ├─ AgentMemoryToolset（MEMORY.md 持久化）
  │     ├─ CheckpointToolset（可选）
  │     ├─ TeamToolset（可选）
  │     └─ 用户自定义 toolsets
  ├─ 3. 组装 all_capabilities[]
  │     ├─ HooksCapability（PRE/POST_TOOL_USE）
  │     ├─ CheckpointMiddleware（可选）
  │     ├─ ContextManagerCapability（自动压缩）
  │     ├─ CostTracking（成本追踪）
  │     ├─ WebSearch / WebFetch / Thinking
  │     └─ 用户自定义 middleware
  ├─ 4. 组装 all_processors[]
  │     ├─ EvictionProcessor（大输出驱逐）
  │     ├─ patch_tool_calls_processor（孤儿修复）
  │     └─ 用户自定义 processors
  ├─ 5. Agent(model, toolsets, capabilities, history_processors, ...)
  └─ 6. @agent.instructions → dynamic_instructions(ctx)
        ├─ uploads_summary
        ├─ todo_prompt
        ├─ console_prompt
        └─ subagent_prompt
```

### 1.3 模块规模热力图

```
agent.py              ████████████████████████████████████  1,033行  ★★★★★ 复杂度最高
skills/toolset.py     ████████████████████               593行  ★★★★
checkpointing.py      ███████████████████                570行  ★★★★
skills/backend.py     ██████████████████                 564行  ★★★
teams.py              ██████████████████                 562行  ★★★
skills/directory.py   █████████████████                  531行  ★★★
skills/types.py       █████████████████                  520行  ★★
hooks.py              ███████████████                    458行  ★★★★
__init__.py           ████████████                       355行  ★
eviction.py           ███████████                        334行  ★★★
spec.py               ██████████                         315行  ★★
skills/local.py       ██████████                         312行  ★★
styles.py             █████████                          281行  ★
deps.py               ████████                           239行  ★★★
memory.py             ████████                           231行  ★★
context.py(toolset)   ███████                            219行  ★★
plan/toolset.py       ███████                            216行  ★★
patch.py              ███████                            208行  ★★★
history_archive.py    ██████                             183行  ★★
prompts.py            ████                               107行  ★
```

---

## 2. 核心模块逐一分析

### 2.1 agent.py — 工厂核心（1,033行）

职责：create_deep_agent() 工厂函数，组装所有组件返回 Agent 实例

关键实现：
- 60+ 参数的工厂函数，2 个 @overload 签名支持泛型输出类型
- _DepsTodoProxy 代理模式：延迟绑定 deps，解决 toolset 创建时 deps 不存在的问题
- _default_deep_agent_factory 闭包：子代理递归创建，关闭 thinking/cost_tracking 节省 token
- dynamic_instructions() 运行时注入：每次 model turn 动态组装系统提示词

代码质量：B+
- 逻辑清晰，组装顺序合理
- 但函数过长（260 行实现体），应拆分为 _build_toolsets() / _build_capabilities() 等

### 2.2 deps.py — DI 容器（239行）

职责：DeepAgentDeps dataclass，持有运行时所有状态

关键实现：
- clone_for_subagent() 共享 backend/files/uploads，隔离 todos/subagents
- upload_file() 自动检测编码（chardet）和 MIME 类型
- __post_init__ 与 StateBackend 的 _files 双向同步

代码质量：B
- upload_files() 静默跳过失败上传（except RuntimeError: pass），应至少 log

### 2.3 hooks.py — 生命周期钩子（458行）

职责：Claude Code 风格的工具生命周期钩子系统

关键实现：
- 8 种事件类型（PRE/POST_TOOL_USE、BEFORE/AFTER_RUN、BEFORE/AFTER_MODEL_REQUEST）
- 命令钩子通过 SandboxProtocol.execute() 执行，exit code 0=允许 / 2=拒绝
- Python 处理器钩子直接 await handler(hook_input)
- 支持 background 模式（fire-and-forget）

代码质量：B-
- 模块中间重复导入（line 250），代码组织有拼接痕迹
- Shell 注入防护仅做了单引号转义，不够健壮

### 2.4 eviction.py — 大输出驱逐（334行）

职责：自动将超大工具输出保存到文件，替换为预览 + 文件引用

关键实现：
- 按 NUM_CHARS_PER_TOKEN = 4 估算 token 数，默认 20K token 阈值
- _evicted_ids set 防止重复驱逐
- 运行时优先使用 ctx.deps.backend，fallback 到构造时的 backend

代码质量：B+
- 实现简洁，边界处理合理（写入失败保留原始内容）
- 但有并发安全隐患（见 Bug 清单）

### 2.5 patch.py — 孤儿工具调用修复（208行）

职责：修复中断对话中的孤儿 ToolCallPart / ToolReturnPart

关键实现：
- Phase 1：找到没有对应 ToolReturnPart 的 ToolCallPart，注入 "Tool call was cancelled."
- Phase 2：找到没有对应 ToolCallPart 的 ToolReturnPart，直接移除
- 两阶段串行处理，Phase 1 的结果作为 Phase 2 的输入

代码质量：A-
- 逻辑清晰，边界处理完善
- 排序保证确定性（sorted(orphaned_ids)）
- 唯一问题：只检查相邻消息，跨消息的孤儿可能漏掉（但实际场景中几乎不会发生）

### 2.6 checkpointing.py — 会话快照（570行）

职责：对话状态快照、回滚、会话分叉

关键实现：
- Checkpoint 不可变快照 + RewindRequested 异常传播回滚信号
- InMemoryCheckpointStore / FileCheckpointStore 双后端
- CheckpointMiddleware 自动快照（every_tool / every_turn / manual_only）
- fork_from_checkpoint() 会话分叉工具函数

代码质量：B-
- FileCheckpointStore 的 async 方法内全是同步 I/O，是最严重的设计问题之一
- _make_checkpoint 浅拷贝 messages，依赖不可变性假设

### 2.7 skills/toolset.py — 技能系统（593行）

职责：技能发现、加载、执行的主集成层

关键实现：
- 4 个工具：list_skills → load_skill → read_skill_resource → run_skill_script
- 渐进式披露：先列表（摘要），再加载（完整指令），再执行（资源/脚本）
- @skills.skill 装饰器支持编程式技能定义
- get_instructions() 自动注入技能摘要到系统提示词

代码质量：A-
- 设计模式优秀（渐进式披露避免 prompt 膨胀）
- 错误处理友好（返回可用列表而非抛异常）
- 支持 exclude_tools 和自定义 descriptions

### 2.8 memory.py — 持久记忆（231行）

职责：跨会话持久化 Agent 记忆（MEMORY.md 文件）

关键实现：
- get_instructions() 自动加载前 N 行到系统提示词
- write_memory 追加模式，update_memory 精确替换
- 每个 agent/subagent 独立记忆文件

代码质量：B+
- 简洁实用
- load_memory() 使用 _read_bytes()（私有方法），与 deps.py 同样的耦合问题

### 2.9 history_archive.py — 历史搜索（183行）

职责：压缩后的完整对话历史搜索

关键实现：
- 读取 messages.json（ContextManagerMiddleware 写入的完整历史）
- 简单的 case-insensitive 子串搜索 + 上下文窗口
- 最多返回 10 条匹配

代码质量：B
- 搜索算法过于简单（无分词、无相关性排序）
- 异常处理过于宽泛（except Exception: pass）

---

## 3. 稳定性分析 & 潜在 Bug

### P0 — 生产环境可能触发

**Bug #1：用户工具注册丢失元数据**

位置：agent.py:958-963

```python
# 当前实现
if tools:
    for tool in tools:
        if isinstance(tool, Tool):
            agent.tool(tool.function)  # ← 只传了裸函数！
        else:
            agent.tool(tool)
```

问题：Tool 对象携带的 prepare、args_validator、max_retries、description、strict、sequential、requires_approval、timeout 等元数据全部丢失。

影响：用户传入 Tool(function=my_fn, prepare=my_prepare, max_retries=5) 时，prepare 和 max_retries 被静默忽略。

修复建议：
```python
if isinstance(tool, Tool):
    agent._function_toolset.add_tool(tool)  # 保留完整 Tool 对象
```

复现：
```python
from pydantic_ai.tools import Tool

def my_prepare(ctx, tool_def):
    # 动态隐藏工具
    return None if ctx.deps.read_only else tool_def

tool = Tool(function=my_fn, prepare=my_prepare, description="Custom tool")
agent = create_deep_agent(tools=[tool])
# my_prepare 永远不会被调用
```

---

**Bug #2：Agent 实例私有属性注入**

位置：agent.py:966-967

```python
agent._context_middleware = context_mw    # type: ignore[attr-defined]
agent._task_manager = _subagent_task_manager  # type: ignore[attr-defined]
```

问题：直接在 pydantic-ai 的 Agent 实例上 setattr 自定义属性。# type: ignore 注释说明作者知道这不安全。

影响：
- pydantic-ai 升级加 __slots__ → AttributeError
- pydantic-ai 升级加同名属性 → 命名冲突
- 其他 capability/middleware 如果也这样做 → 属性覆盖

修复建议：将这些引用存储在 DeepAgentDeps 中，或使用 agent.metadata 字典。

---

**Bug #3：CheckpointMiddleware 类型不安全**

位置：check



**Bug #3：CheckpointMiddleware 类型不安全**

位置：checkpointing.py:361-362

```python
async def before_model_request(self, ctx, request_context: Any) -> Any:
    messages: list[ModelMessage] = request_context.messages  # ← Any 类型
```

问题：request_context 类型为 Any，直接访问 .messages 属性。pydantic-ai 的 before_model_request 回调的 request_context 结构未在文档中承诺稳定。

影响：pydantic-ai 改变 request_context 内部结构时，这里会 AttributeError，导致 checkpoint 功能静默失败（被 pydantic-ai 的异常处理吞掉）。

---

**Bug #4：FileCheckpointStore 同步 I/O 阻塞事件循环**

位置：checkpointing.py:238-285（所有 async 方法）

```python
async def save(self, checkpoint: Checkpoint) -> None:
    self._path_for(checkpoint.id).write_bytes(self._serialize(checkpoint))  # 同步！

async def get(self, checkpoint_id: str) -> Checkpoint | None:
    path = self._path_for(checkpoint_id)
    if not path.exists():        # 同步！
        return None
    return self._deserialize(path.read_bytes())  # 同步！

async def list_all(self) -> list[Checkpoint]:
    checkpoints = []
    for path in sorted(self._dir.glob("*.json")):  # 同步！
        checkpoints.append(self._deserialize(path.read_bytes()))  # 同步！
    return sorted(checkpoints, key=lambda cp: cp.created_at)
```

问题：所有方法声明为 async def 但内部全是同步文件 I/O（write_bytes、read_bytes、glob、exists、unlink）。

影响：
- 每次 checkpoint 操作阻塞整个 asyncio 事件循环
- list_all() 在 checkpoint 多时（最多 20 个）串行读取 20 个 JSON 文件
- 高并发场景下严重影响响应延迟

修复建议：使用 aiofiles 或 asyncio.to_thread() 包装。

---

### P1 — 边界条件 / 数据一致性

**Bug #5：deps.py 访问 StateBackend 私有属性**

位置：deps.py:40-46

```python
def __post_init__(self) -> None:
    if isinstance(self.backend, StateBackend):
        if self.files:
            self.backend._files = self.files          # ← 私有属性
        else:
            object.__setattr__(self, "files", self.backend._files)  # ← hack
```

问题：
1. 直接访问 backend._files（下划线前缀 = 私有 API）
2. object.__setattr__ 绕过 dataclass 的赋值机制

影响：StateBackend 重构内部存储结构时，这里会静默断裂。

---

**Bug #6：write() 参数类型不一致**

位置：eviction.py:240 vs memory.py:190

```python
# eviction.py:240 — 传 str
write_result = backend.write(file_path, content_str)

# memory.py:190 — 传 bytes
backend.write(self._path, new_content.encode("utf-8"))
```

问题：同一个 BackendProtocol.write() 方法，两个调用方传入不同类型。

影响：取决于 write() 的实际签名。如果只接受 str | bytes 其中一种，另一个调用方会类型错误。如果接受 str | bytes 联合类型，则无问题但代码风格不一致。

---

**Bug #7：EvictionProcessor 并发不安全**

位置：eviction.py:171

```python
_evicted_ids: set[str] = field(default_factory=set, repr=False)
```

问题：_evicted_ids 是普通 set，多个并发 agent.run() 共享同一个 EvictionProcessor 实例时，并发读写 set 不是线程安全的。

影响：
- asyncio 单线程场景下安全（协程不会真正并行）
- 但如果使用 asyncio.to_thread 或多线程调用 agent.run()，可能导致 RuntimeError: Set changed size during iteration

严重程度：在纯 asyncio 场景下为 P2，在多线程场景下为 P0。

---

**Bug #8：InMemoryCheckpointStore.remove_oldest() 逻辑缺陷**

位置：checkpointing.py:177-182

```python
async def remove_oldest(self) -> bool:
    if not self._checkpoints:
        return False
    oldest_key = next(iter(self._checkpoints))  # ← 取插入顺序第一个
    del self._checkpoints[oldest_key]
    return True
```

问题：save() 方法覆盖已有 key 时不改变 dict 插入顺序。当 save_checkpoint 工具重新标记一个 checkpoint（用相同 ID 覆盖）时，该 checkpoint 仍在"最老"位置。

场景：
1. 自动创建 checkpoint A（位置 1）
2. 自动创建 checkpoint B（位置 2）
3. 用户调用 save_checkpoint("important") → 覆盖 B 的 label，但 B 的 ID 不变
4. 自动创建 checkpoint C（位置 3）
5. 达到 max_checkpoints → remove_oldest() 删除位置 1 的 A ✓ 正确

但如果用户标记的是 A：
1. 用户调用 save_checkpoint("important") → 覆盖 A（位置 1 不变）
2. 达到 max_checkpoints → remove_oldest() 删除 A ← 用户标记的重要 checkpoint 被删！

修复建议：remove_oldest() 应按 created_at 排序而非插入顺序，或者 save() 覆盖时先 del 再 insert 以更新顺序。

---

### P2 — 代码质量 / 可维护性

**Bug #9：hooks.py 模块中间重复导入**

位置：hooks.py:250

```python
# 文件顶部已有 from dataclasses import dataclass
# ...
# 第 250 行又来一次
from dataclasses import dataclass, field  # noqa: E402
```

分析：模块上半部分定义纯数据类和辅助函数，下半部分定义 HooksCapability（依赖 pydantic-ai）。中间的重复导入暗示这是两个文件拼接而成。虽然功能正确，但增加维护困惑。

---

**Bug #10：hooks.py 假设 execute() 是同步方法**

位置：hooks.py:197

```python
response = await asyncio.to_thread(backend.execute, full_command, hook.timeout)
```

问题：asyncio.to_thread() 将同步函数放到线程池执行。如果某个 backend 实现的 execute() 是 async def，在线程池中调用会返回未 await 的 coroutine。

影响：当前所有 backend 实现（LocalBackend、DockerSandbox）的 execute() 确实是同步的，所以暂时安全。但接口层面没有约束。

---

**Bug #11：后台 hook 任务未追踪**

位置：hooks.py:291（及多处类似）

```python
asyncio.create_task(_run_background_hook(hook, hook_input, backend))
```

问题：创建的 task 没有被保存到任何集合中。Python 的 asyncio 文档明确警告：

> Important: Save a reference to the result of this function, to avoid a task disappearing mid-execution.

影响：
- Task 可能被 GC 回收导致中途取消
- Python 3.12+ 会打印 Task was destroyed but it is pending! 警告
- 无法在 agent 关闭时优雅等待后台 hook 完成

---

**Bug #12：history_archive.py 吞掉异常**

位置：history_archive.py:117-119

```python
try:
    raw = path.read_bytes()
    if raw:
        return list(ModelMessagesTypeAdapter.validate_json(raw))
except Exception:  # pragma: no cover
    pass
return []
```

问题：except Exception 吞掉所有异常，包括 JSON 解析错误、Pydantic 验证错误、权限错误等。

影响：messages.json 损坏时，搜索工具返回 "No conversation history saved yet."，用户无法知道文件已损坏。

---

**Bug #13：默认 skills 目录使用相对路径**

位置：skills/toolset.py:220-231

```python
elif skills is None:
    default_dir = Path("./skills")
    if not default_dir.exists():
        warnings.warn(...)
    else:
        self._load_directory_skills([default_dir])
```

问题：./skills 是相对于进程工作目录的路径，不同启动方式下行为不一致。

---

**Bug #14：checkpoint 浅拷贝依赖不可变性假设**

位置：checkpointing.py:299

```python
def _make_checkpoint(...):
    return Checkpoint(
        ...
        messages=list(messages),  # 浅拷贝
        ...
    )
```

问题：list(messages) 只拷贝列表本身，不拷贝 ModelMessage 对象。如果后续代码修改了 message 对象的内部状态，checkpoint 中的数据也会被改变。

当前风险：pydantic-ai 的 ModelMessage（ModelRequest/ModelResponse）是 dataclass，其 parts 字段是 Sequence（不可变），所以当前安全。但这是一个脆弱的假设。

---

## 4. 设计模式评估

### 优秀的设计

| 模式 | 实现 | 评价 |
|------|------|------|
| 组合优于继承 | Toolset + Capability 自由组合 | 扩展性极好，用户可以只用需要的组件 |
| 渐进式披露 | Skills 三阶段（list → load → run） | 有效控制 prompt 膨胀，token 效率高 |
| 处理器管道 | history_processors 链式处理 | 关注点分离，eviction/patch/summarization 独立 |
| 代理模式 | _DepsTodoProxy 延迟绑定 | 优雅解决 toolset 创建时 deps 不存在的鸡蛋问题 |
| 降级设计 | backend fallback 链 | EvictionProcessor 优先用运行时 deps.backend |

### 需要改进的设计

| 问题 | 现状 | 建议 |
|------|------|------|
| 工厂函数过长 | create_deep_agent() 260 行实现体 | 拆分为 _build_toolsets() / _build_capabilities() |
| 类型安全 | 大量 Any 类型（hooks、middleware、checkpoint） | 定义具体 Protocol 或 TypeVar |
| 私有 API 依赖 | backend._files、backend._read_bytes() | 推动上游暴露公开 API |
| 错误传播 | 多处 except Exception: pass | 至少 log.warning |

---

## 5. 与 pydantic-ai 的耦合度分析

### 强依赖（不可替换）

| 依赖项 | 用途 | 替换成本 |
|--------|------|----------|
| Agent 类 | 核心运行时 | 不可替换 |
| AbstractToolset / FunctionToolset | 所有 toolset 的基类 | 不可替换 |
| AbstractCapability | 所有 capability 的基类 | 不可替换 |
| ModelMessage / ToolCallPart / ToolReturnPart | 消息类型 | 不可替换 |
| RunContext | 工具函数的上下文注入 | 不可替换 |
| HistoryProcessor | 消息处理管道 | 不可替换 |

### 外部包依赖

| 包 | 版本 | 用途 | 替换难度 |
|----|------|------|----------|
| pydantic-ai-backends | — | BackendProtocol、StateBackend、SandboxProtocol | 高（核心抽象） |
| pydantic-ai-summarization | — | ContextManagerCapability | 中（可自建） |
| pydantic-ai-shields | — | CostTracking | 低（可选功能） |
| pydantic-ai-todo | — | TodoToolset | 低（可自建） |
| subagents-pydantic-ai | — | SubagentToolset | 中（核心功能） |

### Super-Agent 的实际依赖面

Super-Agent 仅 3 个导入点：
1. agent_factory.py → create_deep_agent, create_default_deps, StateBackend
2. hooks.py → Hook, HookEvent, HookInput, HookResult


## 降级到原生 pydantic-ai 的工作量估算

| 功能 | 替代方案 | 代码量 | 风险 |
|------|----------|--------|------|
| create_deep_agent() | 直接用 Agent() + 手动组装 | ~150 行 | 中 |
| Hooks 系统 | 改用 AbstractCapability 子类 | ~100 行 | 低 |
| Sub-Agent 编排 | 自建 task() 工具 + Agent 池 | ~300 行 | 高 |
| Skills 系统 | 自建目录扫描 + 渐进加载 | ~400 行 | 中 |
| Todo 工具 | 直接用 pydantic-ai-todo | 0 行 | 无 |
| 文件系统工具 | 直接用 pydantic-ai-backends | 0 行 | 无 |
| Eviction | 移植 eviction.py（无框架依赖） | ~50 行适配 | 低 |
| Patch | 移植 patch.py（纯函数） | 0 行 | 无 |
| Memory | 自建（简单） | ~100 行 | 低 |
| Checkpointing | 移植（无框架依赖） | ~50 行适配 | 低 |

总计：~1,150 行新代码，预计 2-3 周。最大风险在 Sub-Agent 编排。

---

## 6. 生产就绪度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整度 | 9/10 | 覆盖 Agent 开发全链路：工具、技能、记忆、子代理、检查点、成本追踪 |
| 代码质量 | 7/10 | 整体清晰，但有拼接痕迹、过长函数、类型安全不足 |
| 错误处理 | 6/10 | 多处 except Exception: pass，静默失败风险 |
| 并发安全 | 5/10 | FileCheckpointStore 同步阻塞、EvictionProcessor 共享 set |
| 类型安全 | 6/10 | 大量 Any 类型，checkpoint middleware 无类型保证 |
| API 稳定性 | 5/10 | v0.3.3 pre-1.0，8 天 3 个 release，API 快速变化 |
| 文档质量 | 8/10 | 每个模块有完整 docstring，示例代码丰富 |
| 测试覆盖 | 6/10 | 多处 # pragma: no cover，关键路径未覆盖 |
| 可扩展性 | 9/10 | Toolset + Capability 组合模式，扩展极其方便 |
| 生态依赖健康度 | 7/10 | 依赖 pydantic-ai 生态（Pydantic 公司背书），但子包较多 |

**综合评分：6.8 / 10 — 可用于内部项目，生产部署需修复 P0 问题**

---

## 7. 技术选型建议

### 适合使用 pydantic-deep 的场景

- 需要快速搭建 Claude Code 风格的编码 Agent
- 团队熟悉 pydantic-ai 生态
- 单用户 / 低并发场景（避开并发安全问题）
- 可以接受 pre-1.0 API 变动

### 不适合的场景

- 高并发生产环境（FileCheckpointStore 阻塞、EvictionProcessor 并发不安全）
- 需要长期 API 稳定性的产品（v0.3.x，快速迭代中）
- 需要多 Agent 分布式协作（无 A2A 协议，不如 AgentScope）

### 如果选择 pydantic-deep，建议的加固措施

1. **P0 修复**：fork 后修复 Bug #1（工具注册）和 Bug #4（异步 I/O）
2. **并发防护**：生产环境用 InMemoryCheckpointStore 而非 FileCheckpointStore
3. **版本锁定**：`pydantic-deep==0.3.3` 精确锁定，不用 `^0.3`
4. **降级预案**：将 Sub-Agent 编排逻辑封装在独立模块，保留降级到原生 pydantic-ai 的能力

---

报告完。14 个 bug（4 P0 + 4 P1 + 6 P2），每个都带了行号和代码片段，可以直接对照源码验证。