# 目录结构重构方案

## 设计原则

1. **一个支柱一个目录** — 六大架构支柱各自独立，边界清晰
2. **声明与执行分离** — schema/接口定义与运行时实现分开放置
3. **最多两层嵌套** — 避免深层目录导致导入路径过长
4. **基础设施下沉** — LLM 路由、状态管理、安全、监控归入 `infra/`
5. **入口聚合** — 所有对外接口（REST/WebSocket/SSE）统一在 `gateway/`

---

## 目标目录树

```
src_deepagent/
│
├── main.py                         # FastAPI 应用工厂 + lifespan
├── schemas/                        # 全局数据模型（跨支柱共享）
│   ├── agent.py                    # TaskNode, ExecutionDAG, SessionStatus
│   ├── api.py                      # QueryRequest, QueryResponse, EventType
│   ├── sandbox.py                  # SandboxTask, Artifact, SandboxResult
│   └── a2ui.py                     # A2UI 事件模型
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱一：上下文系统
├── context/
│   └── builder.py                  # System Prompt 构建器（12 段模板）
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱二：编排系统
├── orchestrator/
│   ├── reasoning_engine.py         # 五维度复杂度评估 → 四种执行模式
│   ├── agent_factory.py            # 主 Agent 创建（pydantic-ai）
│   ├── hooks.py                    # 循环检测 + 审计钩子
│   └── planning.py                 # DAG 规划 Prompt 模板
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱三：能力系统
├── capabilities/
│   ├── registry.py                 # CapabilityRegistry（统一注册 + 分发）
│   ├── base_tools.py               # 10 内置工具（按职责分组）
│   ├── event_publishing.py         # EventPublishingCapability
│   ├── skill_creator.py            # Skill 创建工具
│   ├── mcp/
│   │   └── client_manager.py       # MCP 多端点管理（延迟加载 + 定期刷新）
│   └── skills/
│       ├── registry.py             # Skill 自动扫描注册
│       └── schema.py               # SkillMeta 数据模型
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱四：执行层
├── workers/
│   ├── base.py                     # BaseWorker 模板方法
│   ├── native/
│   │   └── web_search_worker.py    # 网络搜索 Worker
│   └── sandbox/
│       ├── sandbox_worker.py       # 沙箱任务编排
│       ├── sandbox_manager.py      # 沙箱生命周期（E2B / 本地）
│       ├── pi_agent_config.py      # Pi Agent 启动脚本生成
│       └── ipc.py                  # JSONL IPC 解析
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱五：事件流
├── streaming/
│   ├── protocol.py                 # 事件类型枚举（A2UI 协议）
│   ├── stream_adapter.py           # Redis Streams 读写适配
│   ├── sse_endpoint.py             # SSE 事件生成器（断点续传）
│   └── recovery.py                 # 断点续传恢复逻辑
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 支柱六：记忆系统
├── memory/
│   ├── storage.py                  # MemoryStorage ABC + RedisMemoryStorage
│   ├── schema.py                   # UserProfile, Fact, MemoryData
│   ├── retriever.py                # 记忆检索（200ms 超时降级）
│   └── updater.py                  # 记忆写入 / 更新
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 基础设施层
├── infra/                          # 新增：基础设施聚合目录
│   ├── llm/                        # 原 llm/（整体迁入）
│   │   ├── catalog.py
│   │   ├── registry.py
│   │   ├── schemas.py
│   │   ├── compatibility.py
│   │   ├── token_manager.py
│   │   ├── models.yaml
│   │   └── providers/
│   │       ├── base.py
│   │       ├── anthropic_native.py
│   │       └── openai_compat.py
│   ├── state/                      # 原 state/（整体迁入）
│   │   └── session_manager.py
│   ├── security/                   # 原 security/（整体迁入）
│   │   ├── audit.py
│   │   ├── injection_guard.py
│   │   ├── permissions.py
│   │   └── sandbox_policy.py
│   └── monitoring/                 # 原 monitoring/（整体迁入）
│       ├── langfuse_tracer.py
│       ├── arms_tracer.py
│       ├── metrics.py
│       └── pipeline_events.py
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 对外接口层
├── gateway/
│   ├── rest_api.py                 # REST 路由（/api/agent/query 等）
│   └── websocket_api.py            # WebSocket 连接管理
│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 公共基础
├── core/
│   ├── logging.py                  # 日志系统 + 上下文变量
│   └── exceptions.py               # 自定义异常
├── config/
│   └── settings.py                 # Pydantic BaseSettings（所有配置项）
└── agents/                         # Sub-Agent 工厂（保持不变）
    ├── factory.py
    ├── models.py
    ├── roles.py
    └── custom/
        └── registry.py
```

---

## 迁移映射表

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src_deepagent/llm/` | `src_deepagent/infra/llm/` | 整体迁入 infra |
| `src_deepagent/state/` | `src_deepagent/infra/state/` | 整体迁入 infra |
| `src_deepagent/security/` | `src_deepagent/infra/security/` | 整体迁入 infra |
| `src_deepagent/monitoring/` | `src_deepagent/infra/monitoring/` | 整体迁入 infra |
| `src_deepagent/billing/` | `src_deepagent/infra/billing/` | 整体迁入 infra（新增） |
| 其余模块 | 路径不变 | context / orchestrator / capabilities / workers / streaming / memory / gateway / core / config / agents / schemas |

---

## 模块依赖方向

```
gateway → orchestrator → context → memory
                       → capabilities → workers → streaming
                       → infra/llm
                       → agents
                       → infra/state
                       → infra/security
                       → infra/monitoring
core ← 所有模块（日志、异常）
schemas ← 所有模块（数据模型）
```

依赖规则：
- `infra/` 只被上层模块依赖，自身不依赖业务模块
- `core/` 和 `schemas/` 是叶节点，不依赖其他业务模块
- `streaming/` 只被 `workers/` 和 `gateway/` 依赖，不反向依赖

---

## 关键接口示例

### CapabilityRegistry（能力注册表）

```python
class CapabilityRegistry:
    def register_tool(self, group: str, fn: Callable) -> None: ...
    def register_skill(self, meta: SkillMeta) -> None: ...
    def get_tools(self, groups: list[str]) -> list[Callable]: ...
    def get_mcp_toolsets(self) -> list[MCPToolset]: ...
```

### ReasoningEngine（推理引擎）

```python
class ReasoningEngine:
    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def get_plan(self, query: str, session_id: str) -> ExecutionPlan: ...

@dataclass
class ExecutionPlan:
    mode: ExecutionMode          # DIRECT / AUTO / PLAN_AND_EXECUTE / SUB_AGENT
    prompt_prefix: str
    resources: ResolvedResources
```

### BaseWorker（执行层模板）

```python
class BaseWorker(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    async def execute(self, task: TaskNode) -> WorkerResult: ...  # 模板方法

    @abstractmethod
    async def _do_execute(self, task: TaskNode) -> WorkerResult: ...
```
