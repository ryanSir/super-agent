# Memory 系统重构设计文档

> 状态：设计完成，待实施
> 日期：2026-04-13
> 参考：hermes-agent memory 架构

---

## 一、现状分析

### 当前实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `memory/schema.py` | ✅ 完整 | UserProfile、Fact、MemoryData 数据模型 |
| `memory/storage.py` | ✅ 完整 | MemoryStorage ABC + RedisMemoryStorage 实现 |
| `memory/retriever.py` | ✅ 完整 | MemoryRetriever，200ms 超时降级 |
| `memory/updater.py` | ✅ 完整 | MemoryUpdater，LLM 抽取 + 分布式锁 + 去重 |

### 集成断点（未接通的地方）

| 问题 | 位置 | 影响 |
|------|------|------|
| memory_text 未注入 system prompt | `agent_factory.py:55-61` 调用 `build_dynamic_instructions()` 时未传 `memory_text` | Agent 无法访问用户历史记忆 |
| MemoryUpdater 从未被调用 | `rest_api.py` 会话完成后缺少 `updater.update()` | 对话内容无法被记忆系统学习 |
| recall_memory 工具缺少 redis_client | `base_tools.py` 中 `MemoryRetriever()` 未传入 redis_client | 工具运行时崩溃 |
| user_id 未传递到 memory 操作 | `rest_api.py` 全流程 | 无法区分不同用户的记忆 |

### pydantic-deep 框架内置 Memory

框架通过 `create_deep_agent(include_memory=True)` 提供轻量 memory：
- 存储：MEMORY.md 文件（每个 agent 独立）
- 工具：read_memory / write_memory / update_memory
- 注入：自动注入 system prompt
- 局限：单用户、无语义检索、无安全扫描

当前项目设置 `include_memory=False`，未启用。

---

## 二、目标架构

借鉴 hermes-agent 的 MemoryManager + MemoryProvider 架构，适配多用户 SaaS 场景。

```
MemoryManager（编排器）
├── BuiltinProvider（Redis，多用户）  ← 当前 memory/ 模块封装
│   ├── 用户画像（UserProfile）
│   ├── 事实库（Facts）
│   └── 冻结快照（Frozen Snapshot）
├── [ExternalProvider]（预留，Honcho/Mem0 等）
│   └── 语义召回 / 辩证推理 / ...
└── MemoryTool（LLM 可调用）
    └── add / replace / remove + 安全扫描
```

### 核心设计决策

| 决策 | 选型 | 理由 |
|------|------|------|
| 快照模式 | 冻结快照（hermes 风格） | 会话开始拍快照注入 prompt，mid-session 写入落盘但不改 prompt，保护 prefix cache |
| Provider 架构 | 可插拔，最多 1 个外部 | 内置 Redis + 外部（Honcho/Mem0），避免工具 schema 膨胀和记忆冲突 |
| 安全扫描 | 写入前检测 | prompt injection / 凭证外泄 / 隐形 unicode |
| 与 pydantic-deep memory 的关系 | 并存 | 框架 MEMORY.md 作为 agent 级笔记本，自建 memory 作为用户级画像和事实库 |

---

## 三、hermes-agent 关键设计参考

### 3.1 冻结快照模式

```
会话启动 → load_from_disk() → 拍快照 → 注入 system prompt
                                  ↓
              整个会话期间 system prompt 中的 memory 不变
                                  ↓
              工具写入立即落盘，但不更新当前会话的 prompt
                                  ↓
              下次会话启动时刷新快照
```

核心价值：保护 prompt prefix cache 的稳定性。如果 memory 每轮都变，system prompt 就会变，prefix cache 就失效。

### 3.2 MemoryProvider ABC（hermes 接口）

```python
class MemoryProvider(ABC):
    @property
    def name(self) -> str: ...
    def is_available(self) -> bool: ...
    def initialize(self, session_id, **kwargs) -> None: ...
    def system_prompt_block(self) -> str: ...          # 静态注入
    def prefetch(self, query, *, session_id="") -> str: ...  # 语义召回
    def sync_turn(self, user_content, assistant_content, ...) -> None: ...  # 持久化
    def get_tool_schemas(self) -> list[dict]: ...       # 注册工具
    def handle_tool_call(self, tool_name, args, **kwargs) -> str: ...
    def on_memory_write(self, action, target, content) -> None: ...  # 镜像通知
    def shutdown(self) -> None: ...
```

### 3.3 安全扫描

hermes 在 memory 写入前检测：
- prompt injection（`ignore previous instructions`、`you are now`）
- 角色劫持（`do not tell the user`）
- 凭证外泄（`curl ... $SECRET_KEY`）
- 隐形 unicode（零宽字符注入）

### 3.4 每轮对话 Memory 生命周期

```
1. on_turn_start()        ← 通知 provider 新一轮开始
2. prefetch_all(query)    ← 后台召回相关记忆（缓存结果）
3. 构建 API 请求          ← 将召回内容包裹在 <memory-context> 标签中
4. LLM 响应 + 工具调用
5. sync_turn()            ← 非阻塞地将本轮对话同步到外部 provider
6. queue_prefetch_all()   ← 后台预取下一轮的记忆
```

### 3.5 外部 Provider 对比

| Provider | 特点 |
|----------|------|
| Honcho | 辩证式 Q&A、语义搜索、peer card、持久化结论 |
| Mem0 | 服务端 LLM 事实抽取、语义搜索 + reranking、自动去重、熔断器 |
| Hindsight / Holographic / RetainDB | 插件形式，各有侧重 |

---

## 四、实施计划

### 需要新建的文件

| 文件 | 说明 |
|------|------|
| `memory/provider.py` | MemoryProvider ABC（异步版） |
| `memory/manager.py` | MemoryManager 编排器（快照 + prefetch + sync + 工具路由） |
| `memory/builtin_provider.py` | 内置 Redis Provider（封装现有 storage/retriever/updater） |
| `memory/safety.py` | 安全扫描（prompt injection / 凭证外泄 / 隐形 unicode） |

### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `gateway/rest_api.py` | configure() 初始化 MemoryManager；_run_orchestration() 中拍快照 + sync_turn |
| `orchestrator/agent_factory.py` | create_orchestrator_agent() 新增 memory_text 参数，传入 build_dynamic_instructions() |
| `capabilities/base_tools.py` | 修复 recall_memory 的 redis_client 注入（ContextVar） |
| `memory/retriever.py` | 确保 redis_client 正确传递 |
| `memory/updater.py` | 确保 llm_fn 可外部注入 |

### 不需要改的文件

| 文件 | 理由 |
|------|------|
| `memory/schema.py` | 数据模型完整 |
| `memory/storage.py` | Redis 存储完整，直接复用 |

### 扩展点 — 外部 Provider 接入方式

```python
# 1. 实现 MemoryProvider
class HonchoProvider(MemoryProvider):
    name = "honcho"
    async def prefetch(self, query, *, user_id="", session_id="") -> str: ...
    async def sync_turn(self, user_content, assistant_content, **kwargs): ...

# 2. 注册到 MemoryManager（自动限制最多一个外部 provider）
manager.add_provider(HonchoProvider(api_key="..."))
```

---

## 五、与 pydantic-deep Memory 的关系

两套 memory 并存，各司其职：

| | pydantic-deep MEMORY.md | 自建 Memory（Redis） |
|---|---|---|
| 定位 | Agent 级笔记本 | 用户级画像和事实库 |
| 存储 | 文件 | Redis |
| 多用户 | 不支持 | 支持（user_id 隔离） |
| 写入方 | LLM 主动调工具 | LLM 抽取 + 工具 |
| 注入方式 | 框架自动注入 | 冻结快照注入 |
| 启用方式 | `include_memory=True` | MemoryManager 初始化 |

建议：先启用自建 Memory（修复集成断点），pydantic-deep 的 `include_memory` 保持 False，避免两套 memory 在 system prompt 中冲突。后续如果需要 agent 级笔记本再开启。
