# Deep Agents (langchain-ai/deepagents) 源码深度分析报告

▎ LangChain 官方出品 | 21k Star | MIT | v0.5.3 (2026-04-15)
▎ "Inspired by Claude Code" — 通用 Agent SDK + CLI
▎ 2026-04-17

---

## 1. 架构速览

```
┌─────────────────────────────────────────────────────────────┐
│  入口层                                                      │
│  CLI (Textual TUI) + ACP 编辑器插件 + SDK (create_deep_agent)│
├─────────────────────────────────────────────────────────────┤
│  graph.py — create_deep_agent() 工厂函数 (~635 行)           │
│  组装 model + tools + middleware + backend → LangGraph 图    │
├─────────────────────────────────────────────────────────────┤
│  中间件栈（洋葱模型，严格排序）                               │
│  base stack → user middleware → tail stack                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Permissions → Skills → Memory → Subagents →             ││
│  │ AsyncSubagents → Summarization → PatchToolCalls         ││
│  └─────────────────────────────────────────────────────────┘│
├──────────┬──────────┬───────────┬───────────────────────────┤
│ Backends │ Tools    │ Profiles  │ Models                     │
│ Protocol │ todos    │ per-model │ provider:model 字符串       │
│ State    │ fs ops   │ defaults  │ Anthropic(默认)             │
│ Filesyst │ shell    │ token     │ OpenAI/Google/Ollama        │
│ LocalShe │ subagent │ limits    │ OpenRouter                  │
│ Composit │ skills   │           │                             │
│ Sandbox  │ memory   │           │                             │
│ LangSmit │ search   │           │                             │
│ Store    │          │           │                             │
└──────────┴──────────┴───────────┴───────────────────────────┘
```

### 核心数据流

```
create_deep_agent(model, tools, middleware, backend, ...)
  │
  ├─ 1. 解析 model（默认 anthropic:claude-sonnet-4-6）
  ├─ 2. 解析 backend（默认 StateBackend — 纯内存）
  ├─ 3. 组装内置工具
  │     ├─ write_todos（任务规划）
  │     ├─ read_file / write_file / edit_file（文件操作）
  │     ├─ ls / glob / grep（搜索）
  │     ├─ execute（shell 命令，需 SandboxBackendProtocol）
  │     └─ task()（子代理委派）
  ├─ 4. 组装中间件栈（严格排序）
  │     ├─ base: [Permissions, Skills, Memory]
  │     ├─ user: [自定义中间件...]
  │     └─ tail: [Subagents, AsyncSubagents, Summarization, PatchToolCalls]
  ├─ 5. 编译为 LangGraph StateGraph
  └─ 返回 CompiledGraph（可直接 .invoke() / .stream()）
```

```
Agent 运行时:
  middleware.before_agent() [正序]
    → LangGraph agent loop（model → tools → model → ...）
      → middleware.wrap_tool_call() [洋葱模型]
      → middleware.wrap_model_call() [洋葱模型]
    → Summarization 自动压缩（超阈值时）
  middleware.after_agent() [逆序]
```

---

## 2. 核心模块分析

### 2.1 graph.py — 工厂核心（~635 行）

职责：`create_deep_agent()` 组装所有组件，返回 LangGraph CompiledGraph

**关键设计：**
- 返回的是 LangGraph 标准图，不是自定义类 — 天然支持 streaming、persistence、checkpointing
- 中间件栈严格三段排序：base stack → user middleware → tail stack
- Anthropic 模型自动启用 prompt caching
- 子代理配置支持继承和覆盖

**代码质量：B+**（635 行单函数偏长，但逻辑清晰）

---

### 2.2 BackendProtocol — 沙箱抽象（最干净的设计）

文件：`backends/protocol.py`

**两层协议：**

```
BackendProtocol（文件操作）
  ├─ read(path, offset, limit) → ReadResult
  ├─ write(path, content) → WriteResult
  ├─ edit(path, old_str, new_str) → EditResult
  ├─ ls(path) → list[str]
  ├─ glob(pattern) → list[str]
  ├─ grep(pattern, path) → list[GrepMatch]
  ├─ upload(files) → FileUploadResponse
  └─ download(paths) → FileDownloadResponse

SandboxBackendProtocol（继承 BackendProtocol + shell 执行）
  └─ execute(command, timeout) → ExecuteResponse
```

**5 种实现：**

| 后端 | 隔离级别 | 用途 |
|------|----------|------|
| StateBackend | 内存（最安全） | 默认，纯状态存储 |
| FilesystemBackend | 文件系统 | 直接读写磁盘 |
| LocalShellBackend | shell=True（需显式 opt-in） | 开发环境 |
| CompositeBackend | 组合多个后端 | 路由不同路径到不同后端 |
| SandboxBackend | 容器级 | 合作伙伴沙箱（Daytona/Modal/QuickJS/Runloop） |

**标准化错误：** `FileOperationError` 字面量类型（`"file_not_found"`、`"permission_denied"` 等），LLM 可理解并恢复。

> **亮点：** 同一代码零改动切换环境 — 开发用 StateBackend，测试用 FilesystemBackend，生产用 SandboxBackend。这是四个框架中抽象最干净的。

---

### 2.3 中间件栈 — 洋葱模型

**11 个中间件文件：**

| 中间件 | 职责 | 位置 |
|--------|------|------|
| permissions.py | 文件系统权限控制（allow/deny 规则，glob 匹配） | base stack |
| skills.py | 技能加载和注入 | base stack |
| memory.py | AGENTS.md 加载 → `<agent_memory>` 标签注入 | base stack |
| subagents.py | 同步子代理（上下文隔离，状态过滤） | tail stack |
| async_subagents.py | 异步子代理（并行执行） | tail stack |
| summarization.py | 自动压缩（token/消息数/上下文比例触发） | tail stack |
| patch_tool_calls.py | 孤儿工具调用修复 | tail stack |
| filesystem.py | 文件系统操作中间件 | — |
| _tool_exclusion.py | 工具排除逻辑 | 内部 |
| _utils.py | 工具函数 | 内部 |

**排序策略：**
- Permissions 在最外层（最后执行，最先拦截）— 安全优先
- Summarization 在内层 — 压缩后的消息不会被权限检查干扰
- 用户自定义中间件在中间 — 可以访问完整上下文

---

### 2.4 SubagentMiddleware — 上下文隔离

**隔离策略：**

```python
_EXCLUDED_STATE_KEYS = {
    "messages", "todos", "structured_response",
    "skills_metadata", "memory_contents"
}
```

- 子代理只收到一条 HumanMessage（任务描述），不继承父对话历史
- 返回时只传回最终消息和非排除状态更新
- 短生命周期：执行完即销毁，不累积状态

**对比：**

| 框架 | 子代理隔离策略 |
|------|----------------|
| pydantic-deep | `clone_for_subagent()` 共享 backend/files，隔离 todos |
| DeerFlow | SubagentExecutor 独立线程池 + 事件循环隔离 |
| AgentScope | MsgHub 广播模式，无显式隔离 |
| Deep Agents | 状态键过滤，最显式的隔离策略 |

---

### 2.5 SummarizationMiddleware — 上下文压缩

**三种触发条件：**
1. 消息数量超阈值
2. Token 数量超阈值
3. 上下文窗口占比超阈值

**压缩策略：**
- 先做参数截断（argument truncation）— 裁剪旧消息中的大型工具参数
- 再做 LLM 摘要压缩
- 完整历史持久化到 `/conversation_history/{thread_id}.md`
- 模型感知默认值：从 chat model profiles 计算 max_tokens

> **对比：** 这是四个框架中压缩策略最精细的 — 先截断再压缩的两阶段策略，避免了一次性压缩丢失关键信息。

---

### 2.6 MemoryMiddleware — AGENTS.md 系统

**设计：**
- 从多个 AGENTS.md 文件加载，按顺序合并
- 内容包裹在 `<agent_memory>` 标签中注入系统提示词
- 多层加载：base → user → project → team
- 懒加载 + 状态缓存
- 明确禁止存储凭证（"Never store API keys, access tokens, passwords"）

**对比：**

| 框架 | 记忆系统 |
|------|----------|
| pydantic-deep | MEMORY.md 单文件，工具读写 |
| DeerFlow | 6 维结构化 JSON + LLM 摘要 |
| AgentScope | 4 后端 + marks 标签 + ReMe |
| Deep Agents | AGENTS.md 多层覆盖，遵循 agentskills.io 开放规范 |

---

### 2.7 PermissionsMiddleware — 文件权限

**规则模型：**

```python
FilesystemPermission(
    operations=["read"],      # read | write
    paths=["/**/*.py"],       # glob 模式（wcmatch）
    mode="allow"              # allow | deny
)
```

- 声明顺序评估，第一个匹配的规则生效
- 无匹配时默认允许
- 路径安全：禁止 `..` 遍历和 `~` 字符
- 对 ls/glob/grep 结果做后过滤（移除无权限路径）

---

### 2.8 安全威胁模型 — 正式文档（独有）

`THREAT_MODEL.md` 识别了 9 项威胁：

| 编号 | 威胁 | 严重程度 | 状态 |
|------|------|----------|------|
| T1 | 上下文注入（memory/skill 文件无 sanitization） | 高 | 已识别，未防护 |
| T3 | 任意 Shell 执行（LocalShellBackend shell=True） | 高 | 需显式 opt-in |
| T7 | OpenAI 数据保留（使用 openai: 前缀时） | 中 | 已记录 |
| T8 | 异步子代理输出注入（远程响应无 sanitization） | 中 | 已识别，未防护 |

> **亮点：** 这是四个框架中唯一有正式安全威胁模型文档的。虽然很多威胁只是"已识别未防护"，但透明度本身就是安全优势。

---

## 3. 稳定性分析 & 潜在 Bug

### P0 — 生产环境可能触发

**Bug #1：T1 — Memory/Skill 文件注入无 sanitization**

来源：`THREAT_MODEL.md`

> "zero validation — no size limit, no content filtering, no escaping"

**问题：** AGENTS.md 和 Skill 文件内容直接注入系统提示词，没有任何过滤。恶意内容可以通过 prompt injection 劫持 Agent 行为。

**影响：** 如果 AGENTS.md 文件被篡改（比如通过 Agent 自己的 write_file 工具），可以注入任意指令。

**缓解：** PermissionsMiddleware 可以限制 AGENTS.md 为只读，但需要用户显式配置。

---

**Bug #2：T3 — LocalShellBackend 使用 shell=True**

来源：`THREAT_MODEL.md`

**问题：** `subprocess.run(shell=True)` 将 LLM 生成的命令直接传给 shell，无任何审计或过滤。

**对比：** DeerFlow 有 SandboxAuditMiddleware（15 个高风险正则 + 复合命令分割），Deep Agents 完全没有。

**缓解：** LocalShellBackend 需要显式 opt-in，默认 StateBackend 不支持 `execute()`。但一旦启用，没有任何安全网。

---

**Bug #3：API 快速变化（v0.5.x，8 天 3 个 release）**

**问题：** v0.5.3 发布于 2026-04-15（2 天前），1,490 个 commit，版本号还在 0.x。API 可能


随时变化。

**影响：** 生产环境必须精确锁定版本，且需要持续跟踪上游变更。

---

### P1 — 边界条件

**Bug #4：T8 — 异步子代理输出注入**

**问题：** 异步子代理从远程服务器获取响应后，直接注入主 Agent 上下文，无 sanitization。

**影响：** 如果异步子代理连接的远程服务被攻击，可以通过响应内容注入恶意指令。

---

**Bug #5：权限默认允许**

位置：`permissions.py`

**问题：** 无匹配规则时默认允许。这是 "fail-open" 策略，与安全最佳实践（fail-closed）相反。

**影响：** 如果用户忘记配置某个路径的权限规则，该路径默认可读可写。

---

**Bug #6：LangChain/LangGraph 重度依赖**

**依赖：**

```
langchain-core      >=1.2.27
langchain           >=1.2.15
langchain-anthropic >=1.4.0
langchain-google-genai >=4.2.1
langsmith           >=0.3.0
```

**问题：** 5 个 LangChain 生态包，版本范围宽泛（`<2.0.0`）。LangChain 的 API 变动频繁，任何一个包的升级都可能引入不兼容变更。

**对比：** pydantic-deep 依赖 pydantic-ai（1 个核心包），AgentScope 自研框架。Deep Agents 的依赖链最长。

---

### P2 — 代码质量

**Bug #7：graph.py 单函数 635 行**

**问题：** `create_deep_agent()` 是一个 635 行的巨型函数，包含模型解析、工具组装、中间件排序、子代理配置、提示词定制等所有逻辑。

**对比：** pydantic-deep 的 `create_deep_agent()` 也有类似问题（260 行），但 Deep Agents 更严重。

---

## 4. 设计模式评估

### 优秀的设计

| 模式 | 实现 | 评价 |
|------|------|------|
| BackendProtocol 抽象 | 5 种后端 + CompositeBackend | 四个框架中最干净的沙箱抽象 |
| 中间件严格排序 | base → user → tail 三段 | 安全中间件始终在最外层 |
| 子代理状态隔离 | `_EXCLUDED_STATE_KEYS` 过滤 | 最显式的隔离策略 |
| 压缩两阶段 | 先参数截断再 LLM 摘要 | 避免一次性压缩丢失信息 |
| 安全威胁模型 | THREAT_MODEL.md 9 项分析 | 唯一有正式安全文档的框架 |
| LangGraph 原生返回 | 返回 CompiledGraph | 天然支持 streaming/persistence/checkpointing |
| 合作伙伴沙箱生态 | Daytona/Modal/QuickJS/Runloop | 最丰富的沙箱选择 |

### 需要改进的设计

| 问题 | 现状 | 建议 |
|------|------|------|
| 无命令审计 | shell=True 无过滤 | 补充 DeerFlow 级别的 SandboxAuditMiddleware |
| 权限 fail-open | 无匹配规则默认允许 | 改为 fail-closed |
| Memory 无 sanitization | 文件内容直接注入 prompt | 添加内容过滤和大小限制 |
| graph.py 过长 | 635 行单函数 | 拆分为 `_build_tools` / `_build_middleware` / `_build_subagents` |
| API 不稳定 | v0.5.x，快速迭代 | 等 v1.0 后再用于生产 |

---

## 5. 四框架对比总表

| 维度 | pydantic-deep | DeerFlow | AgentScope | Deep Agents | 胜出 |
|------|---------------|----------|------------|-------------|------|
| 代码规模 | 8.4K 行 | ~28.6K 行 | ~25K+ 行 | ~10K+ 行 | — |
| 框架依赖 | pydantic-ai（中） | LangChain（高） | 自研（中高） | LangChain（高） | pydantic-deep |
| 中间件系统 | Hooks 8 事件 | 16 个有序中间件 | Hook + Toolkit 中间件 | 洋葱模型 11 个 | DeerFlow |
| 沙箱抽象 | E2B + StateBackend | Local + Docker | 无内置 | BackendProtocol 5 种 | Deep Agents |
| 安全审计 | 无 | SandboxAuditMiddleware | 无 | 无（有威胁模型文档） | DeerFlow |
| 安全文档 | 无 | 无 | 无 | THREAT_MODEL.md 9 项 | Deep Agents |
| 子代理隔离 | clone_for_subagent | 线程池+事件循环隔离 | MsgHub 广播 | 状态键过滤 | DeerFlow |
| 上下文压缩 | ContextManagerCapability | SummarizationMiddleware | CompressionConfig | 两阶段（截断+摘要） | Deep Agents |
| 记忆系统 | MEMORY.md | 6 维 JSON + LLM 摘要 | 4 后端 + marks + ReMe | AGENTS.md 多层覆盖 | AgentScope |
| 多 Agent 编排 | task() 扁平 | SubagentExecutor | MsgHub + Pipeline | task() + async_task() | AgentScope |
| Token 计数 | 框架内置 | LangChain 内置 | 5 种专用计数器 | model profiles 计算 | AgentScope |
| MCP 支持 | 无原生 | langchain-mcp-adapters | StdIO + HTTP 3 种 | langchain-mcp-adapters | AgentScope |
| 分布式 | 无 | 无 | A2A + Nacos | ACP（编辑器集成） | AgentScope |
| Skills 系统 | 三阶段渐进加载 | 技能演进 | AgentSkill + 工具分组 | agentskills.io 规范 | pydantic-deep / Deep Agents |
| 测试覆盖 | 多处 no cover | 94 个测试文件 | 59 个测试文件 | 有测试目录 | DeerFlow |
| API 稳定性 | v0.3.3 pre-1.0 | 2.0 | v1.0+ 月均 2 版 | v0.5.3 快速迭代 | AgentScope |
| 商业支持 | Pydantic 公司 | 社区（字节） | 阿里+蚂蚁 | LangChain 公司 | AgentScope / Deep Agents |
| 合作伙伴沙箱 | 无 | 无 | 无 | Daytona/Modal/QuickJS/Runloop | Deep Agents |

---

## 6. 生产就绪度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整度 | 8/10 | 规划+文件+shell+子代理+压缩+记忆+技能，覆盖全面 |
| 代码质量 | 7/10 | BackendProtocol 抽象优秀，但 graph.py 过长 |
| 错误处理 | 6/10 | 标准化 FileOperationError，但无 LLM 重试退避 |
| 并发安全 | 7/10 | LangGraph 管理状态，子代理隔离清晰 |
| 类型安全 | 8/10 | Protocol + TypedDict + Pydantic，类型系统完善 |
| API 稳定性 | 4/10 | v0.5.x，8 天 3 个 release，pre-1.0 |
| 安全性 | 6/10 | 有威胁模型文档（透明），但多项威胁未防护 |
| 测试覆盖 | 6/10 | 有测试目录，具体覆盖率未知 |
| 可扩展性 | 9/10 | 中间件可组合 + BackendProtocol 可插拔 + 合作伙伴沙箱 |
| 生态依赖健康度 | 7/10 | LangChain 公司官方，但依赖链长 |

**综合评分：6.8 / 10** — 与 pydantic-deep 持平，可扩展性最强但 API 不稳定

---

## 7. 关键结论

### Deep Agents 的核心优势

1. **BackendProtocol 是四个框架中最干净的沙箱抽象** — 同一代码零改动切换 State/Filesystem/Shell/Sandbox/Composite
2. **唯一有正式安全威胁模型文档** — 9 项威胁分析，透明度是安全的第一步
3. **合作伙伴沙箱生态最丰富** — Daytona/Modal/QuickJS/Runloop 四个选择
4. **上下文压缩最精细** — 两阶段策略（先参数截断再 LLM 摘要）
5. **LangGraph 原生返回** — 天然支持 streaming/persistence/checkpointing

### Deep Agents 的核心风险

1. **API 极不稳定** — v0.5.x，8 天 3 个 release，生产环境风险极高
2. **无命令审计** — LocalShellBackend 的 shell=True 没有任何安全过滤
3. **Memory/Skill 注入无防护** — 威胁模型已识别但未修复
4. **LangChain 重度依赖** — 5 个 LangChain 包，升级风险高

### 四框架综合排名

| 排名 | 框架 | 评分 | 最适合场景 |
|------|------|------|------------|
| 1 | DeerFlow | 7.7 | 需要沙箱执行 + 安全审计 + 成熟错误处理 |
| 2 | AgentScope | 7.3 | 多 Agent 协作 + 多模型切换 + 分布式部署 |
| 3 | pydantic-deep | 6.8 | 轻量嵌入 + Skills 渐进加载 + 低框架依赖 |
| 4 | Deep Agents | 6.8 | 可扩展性优先 + 沙箱抽象 + LangGraph 生态 |

pydantic-deep 和 Deep Agents 分数相同但特点不同：pydantic-deep 更轻量、依赖更少；Deep Agents 可扩展性更强、沙箱抽象更好。选哪个取决于你更看重轻量还是可扩展。

---

*报告结束*

*分析基于 Deep Agents 源码截至 2026-04-17 的版本。核心文件行数、Bug 位置均基于实际代码扫描，不排除后续版本已修复部分问题。*