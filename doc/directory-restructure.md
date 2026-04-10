# 目录结构重构方案

## 设计原则

1. **一个支柱一个目录** — 九大模块各有独立目录，边界清晰
2. **声明与执行分离** — capabilities（能做什么）和 workers（怎么做）分开
3. **未实现的预留目录** — 放 `__init__.py` + 模块说明，不留空目录
4. **最多两层嵌套** — 避免目录过深

## 目录结构

```
src_deepagent/
├── main.py                              # FastAPI 入口 + lifespan
├── config/
│   └── settings.py                      # Pydantic BaseSettings
│
├── core/                                # 核心基础设施（跨模块共享）
│   ├── logging.py                       # 结构化日志
│   ├── exceptions.py                    # 异常层级
│   └── types.py                         # 共享类型定义
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 1: 上下文系统 — 决定模型"知道什么"                │
│  └─────────────────────────────────────────────────────────┘
├── context/
│   ├── __init__.py
│   ├── builder.py                       # 上下文组装器（替代 prompts/system.py）
│   ├── runtime.py                       # 运行时上下文（session/user/env）
│   └── templates/                       # 提示词模板（独立维护）
│       ├── role.md
│       ├── runtime_context.md
│       ├── thinking_style.md
│       ├── clarification.md
│       ├── mode_direct.md
│       ├── mode_auto.md
│       ├── mode_plan_and_execute.md
│       ├── mode_sub_agent.md
│       ├── tool_usage.md
│       ├── subagent_system.md
│       ├── response_style.md
│       └── critical_reminders.md
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 2: 工具系统 — 决定模型"能做什么"                  │
│  └─────────────────────────────────────────────────────────┘
├── capabilities/
│   ├── __init__.py
│   ├── registry.py                      # 统一能力注册表
│   ├── base_tools.py                    # 10 个内置工具（从 bridge.py 迁移）
│   ├── skills/                          # Skills 子系统
│   │   ├── __init__.py
│   │   ├── registry.py                  # 三阶段渐进加载注册表
│   │   └── schema.py                    # SkillMetadata / SkillInfo
│   └── mcp/                             # MCP 子系统
│       ├── __init__.py
│       └── deferred_registry.py         # 渐进式加载注册表
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 3: 记忆系统 — 决定模型"记得什么"                  │
│  └─────────────────────────────────────────────────────────┘
├── memory/
│   ├── __init__.py
│   ├── storage.py                       # MemoryStorage ABC（含 consolidate/search 扩展点）
│   ├── retriever.py                     # 记忆检索（200ms 超时降级）
│   ├── updater.py                       # LLM 抽取 + 分布式锁更新
│   └── schema.py                        # UserProfile / Fact / MemoryData
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 4: Agent 协作 — 决定"任务怎么分工"                │
│  └─────────────────────────────────────────────────────────┘
├── orchestrator/
│   ├── __init__.py
│   ├── reasoning_engine.py              # 推理引擎（意图+复杂度+模式路由）
│   ├── agent_factory.py                 # 主 Agent 工厂
│   ├── hooks.py                         # 事件钩子（推送/循环检测）
│   └── planning.py                      # DAG 规划 prompt
│
├── agents/                              # Agent 定义（替代 sub_agents/）
│   ├── __init__.py
│   ├── factory.py                       # Sub-Agent 配置工厂（预置 + 自定义合并）
│   ├── models.py                        # SubAgentInput / SubAgentOutput
│   ├── roles.py                         # 预置角色 System Prompt
│   └── custom/                          # 自定义 Agent（Agent OS）
│       ├── __init__.py
│       └── registry.py                  # AGENT.md 扫描 + 注册
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 5: 安全系统 — 决定"边界在哪里"                    │
│  └─────────────────────────────────────────────────────────┘
├── security/
│   ├── __init__.py
│   ├── permissions.py                   # 工具级权限模型（allow/deny/ask）
│   ├── sandbox_policy.py                # 沙箱安全策略（网络/文件/进程）
│   ├── injection_guard.py               # Prompt 注入检测
│   └── audit.py                         # 审计日志（工具调用链追踪）
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 6: 全链路监控                                     │
│  └─────────────────────────────────────────────────────────┘
├── monitoring/
│   ├── __init__.py
│   ├── arms_tracer.py                   # ARMS 应用监控（链路追踪）
│   ├── langfuse_tracer.py               # Langfuse 模型交互监控
│   ├── metrics.py                       # Prometheus 指标导出（→ Grafana）
│   └── pipeline_events.py              # 管道事件（步骤计时/元数据）
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 7: 事件流                                         │
│  └─────────────────────────────────────────────────────────┘
├── streaming/
│   ├── __init__.py
│   ├── protocol.py                      # 前后端数据协议定义（EventType 枚举）
│   ├── stream_adapter.py                # Redis Streams 适配器
│   ├── sse_endpoint.py                  # SSE 端点
│   └── recovery.py                      # 中断恢复 + 断点续传
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 8: LLM Provider                                   │
│  └─────────────────────────────────────────────────────────┘
├── llm/
│   ├── __init__.py
│   ├── provider.py                      # 多提供商管理（路由 + 降级 + 重试）
│   ├── config.py                        # 模型配置工厂
│   └── token_manager.py                 # 沙箱临时 JWT
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  支柱 9: Token 计费                                     │
│  └─────────────────────────────────────────────────────────┘
├── billing/
│   ├── __init__.py
│   ├── tracker.py                       # 用量追踪（per request/session/user）
│   ├── quota.py                         # 配额管理（限额 + 告警）
│   └── reporter.py                      # 用量报告（日/周/月汇总）
│
│  ┌─────────────────────────────────────────────────────────┐
│  │  执行层 + 网关 + 状态 + 数据模型                        │
│  └─────────────────────────────────────────────────────────┘
├── workers/                             # 执行层（确定性执行器）
│   ├── __init__.py
│   ├── base.py                          # WorkerProtocol + BaseWorker
│   ├── native/
│   │   ├── rag_worker.py
│   │   ├── db_query_worker.py
│   │   └── api_call_worker.py
│   └── sandbox/
│       ├── sandbox_worker.py
│       ├── sandbox_manager.py
│       ├── pi_agent_config.py
│       └── ipc.py
│
├── gateway/                             # API 网关
│   ├── __init__.py
│   ├── rest_api.py
│   └── websocket_api.py
│
├── state/                               # 状态管理
│   ├── __init__.py
│   └── session_manager.py
│
└── schemas/                             # 共享数据模型
    ├── __init__.py
    ├── agent.py                         # TaskNode / ExecutionDAG / OrchestratorOutput
    ├── api.py                           # QueryRequest / QueryResponse
    └── sandbox.py                       # SandboxTask / SandboxResult / Artifact
```

## 迁移映射

```
旧路径                                    → 新路径
──────────────────────────────────────    ──────────────────────────────────
orchestrator/prompts/system.py           → context/builder.py
orchestrator/prompts/templates/          → context/templates/
orchestrator/prompts/planning.py         → orchestrator/planning.py
orchestrator/deferred_tools.py           → capabilities/mcp/deferred_registry.py
orchestrator/custom_agents.py            → agents/custom/registry.py
sub_agents/bridge.py                     → capabilities/base_tools.py
sub_agents/factory.py                    → agents/factory.py
sub_agents/models.py                     → agents/models.py
sub_agents/prompts.py                    → agents/roles.py
skills/registry.py                       → capabilities/skills/registry.py
skills/schema.py                         → capabilities/skills/schema.py
（新增）                                  → security/（预留）
（新增）                                  → billing/（预留）
（新增）                                  → streaming/protocol.py（预留）
（新增）                                  → streaming/recovery.py（预留）
（新增）                                  → llm/provider.py（预留）
（新增）                                  → monitoring/arms_tracer.py（预留）
（新增）                                  → monitoring/metrics.py（预留）
```

## 模块依赖关系

```
gateway → orchestrator → capabilities → workers
              ↓               ↓
           agents          context
              ↓               ↓
           memory         templates/
              
security → 横切所有模块（AOP 方式）
monitoring → 横切所有模块
streaming → gateway + orchestrator
billing → llm + orchestrator
state → gateway
```

## capabilities/registry.py 的作用

```python
class CapabilityRegistry:
    """统一能力注册表 — 汇总所有工具来源
    
    替代 ReasoningEngine._resolve_resources() 中散落的各种 import。
    """
    
    def __init__(self, workers):
        self._base_tools = create_base_tools(workers)
        self._skill_registry = SkillRegistry()
        self._mcp_registry = DeferredToolRegistry()
    
    def get_agent_tools(self) -> list[Callable]:
        """所有 base tools"""
        return self._base_tools
    
    def get_prompt_context(self) -> PromptContext:
        """注入 prompt 的文本"""
        return PromptContext(
            skill_summary=self._skill_registry.get_skill_summary(),
            deferred_tool_names=self._mcp_registry.get_tool_names(),
        )
```

## agents/factory.py 的作用

```python
def create_all_agent_configs(agent_tools, custom_dir="agents") -> list[dict]:
    """合并预置角色 + 自定义角色"""
    from agents.custom.registry import CustomAgentRegistry

    tool_map = {t.__name__: t for t in agent_tools}
    
    # 预置角色（researcher/analyst/writer）
    builtin = create_builtin_configs(tool_map)
    
    # 自定义角色（扫描 agents/ 目录）
    custom_registry = CustomAgentRegistry()
    custom_registry.scan(custom_dir)
    custom = custom_registry.to_sub_agent_configs(tool_map)
    
    return builtin + custom
```