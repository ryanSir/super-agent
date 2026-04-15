# MCP 工具系统：方案对比与架构设计

> 整理时间：2026-04-16

## 1. 背景

Super Agent 需要接入外部 MCP（Model Context Protocol）工具服务，让 LLM 能够调用第三方能力（如火车票查询、专利检索等）。pydantic-deep 框架提供了原生的 MCP Capability 接入方式，但在实际生产接入过程中遇到了协议兼容、参数注入、运维灵活性三个问题，因此在 FastMCPToolset 之上自建了一层管理层。

## 2. pydantic-deep 原生方式

```python
from pydantic_ai.capabilities import MCP, PrefixTools
from pydantic_deep import create_deep_agent

agent = create_deep_agent(
    capabilities=[
        PrefixTools(MCP(url="https://github-mcp.example.com"), prefix="github"),
        PrefixTools(MCP(url="https://slack-mcp.example.com"), prefix="slack"),
    ],
    subagent_extra_toolsets=[mcp.get_toolset()],  # 子 agent 自动继承
)
```

全托管，零配置。框架自动处理连接管理、工具发现、schema 暴露、命名冲突、子 agent 传递。

## 3. 当前方案架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MCPClientManager                         │
│  环境变量驱动 · 多端点管理 · 定期刷新 · 资源缓存            │
├─────────────────────────────────────────────────────────────┤
│                   DefaultArgsToolset                        │
│  参数自动注入 · schema 字段隐藏                              │
├─────────────────────────────────────────────────────────────┤
│                    PrefixedToolset                          │
│  pydantic-ai 原生 · 多端点命名空间隔离                       │
├─────────────────────────────────────────────────────────────┤
│                    FastMCPToolset                           │
│  pydantic-ai 原生 · 工具发现 · schema 暴露 · function call  │
├─────────────────────────────────────────────────────────────┤
│           SSETransport / StreamableHttpTransport            │
│  fastmcp 原生 · MCP 协议通信                                │
└─────────────────────────────────────────────────────────────┘
```

底下三层全部复用 pydantic-ai 和 fastmcp 的原生实现，我们只在上面加了 MCPClientManager 和 DefaultArgsToolset 两层。

配置示例：

```json
MCP_SERVERS=[
  {"name": "search", "url": "https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw"},
  {"name": "trainService", "url": "http://mcp.ly.com/trainmcpserver?api_key=...", "transport": "sse", "default_args": {"api_key": "bce-v3/ALTAK-..."}}
]
```

## 4. 逐项对比

### 4.1 协议层：完全复用 fastmcp

两种方案在协议层没有区别。pydantic-deep 的 `MCP(url=...)` 内部也是创建 fastmcp transport。我们显式用 `SSETransport` / `StreamableHttpTransport` 是因为需要控制协议选择和传入 headers，但协议实现本身没有重写一行。

### 4.2 工具发现与 schema：完全复用 FastMCPToolset

`FastMCPToolset` 负责连接 MCP server、list_tools、把 MCP 工具 schema 转为 pydantic-ai 的 `ToolDefinition`、执行 call_tool。这一层我们完全没动，和 pydantic-deep MCP Capability 底层走的是同一套代码。

### 4.3 命名空间：复用 PrefixedToolset

多端点工具名冲突的处理，pydantic-deep 用 `PrefixTools(MCP(...), prefix="github")`，我们用 `toolset.prefixed("github")`。底层都是 pydantic-ai 的 `PrefixedToolset`，同一个类。

### 4.4 协议选择：我们增强了

pydantic-deep 的 `MCP(url=...)` 依赖 fastmcp 的 URL 路径推断逻辑：

```python
# fastmcp 源码
if re.search(r"/sse(/|\?|&|$)", path):
    return "sse"
else:
    return "http"  # 默认 Streamable HTTP
```

实测发现对 URL 不含 `/sse` 的纯 SSE 服务会失败（405 Method Not Allowed）。

我们通过 `transport` 配置字段显式指定协议，绕过推断逻辑。不配置时仍走 fastmcp 自动推断，向后兼容。

| 服务 | 协议 | 自动推断 | 显式配置 |
|------|------|---------|---------|
| 智慧芽 eureka_claw | Streamable HTTP | 成功 | 不需要 |
| 同程火车票 trainmcpserver | SSE | 失败（405） | `"transport": "sse"` |

### 4.5 参数注入：pydantic-deep 没有

`DefaultArgsToolset` 是我们独有的。它做两件事：

- `get_tools` 时从 `parameters_json_schema` 中移除 `default_args` 对应的字段和 required 约束 → LLM 看不到这些参数
- `call_tool` 时自动合并 `default_args` 到调用参数（LLM 传的值优先）→ MCP server 收到完整参数

这解决了第三方 MCP 服务把认证信息暴露为工具参数的设计缺陷。pydantic-deep 的 MCP Capability 没有这个能力，碰到这类服务只能改服务端或在 prompt 里硬塞 key。

### 4.6 缓存管理：两层缓存

pydantic-deep 的 MCP Capability 没有缓存管理，每次创建 Agent 都重新连接。我们有两层：

**第一层：FastMCPToolset 内置缓存**

`cache_tools=True`（默认开启），连接建立后缓存工具列表，同一个 toolset 实例内不会重复 list_tools。

**第二层：ReasoningEngine 资源缓存**

`_resources_cache` 缓存首次构建的 `ResolvedResources`（包含 agent_tools + mcp_toolsets + prompt_ctx），后续请求直接复用，避免重复创建 base_tools 和获取 skill_summary。

**缓存失效时机：**

| 触发方式 | 机制 | 影响范围 |
|---------|------|---------|
| 定期刷新 | `_refresh_loop` 每 `MCP_REFRESH_INTERVAL` 秒执行 | 重建 toolset 实例 + 清除资源缓存 |
| 手动刷新 | `POST /admin/reload-mcp` 运维接口 | 同上 |
| 应用重启 | lifespan startup | 全部重建 |

### 4.7 配置管理：环境变量 vs 硬编码

```python
# pydantic-deep：写在代码里
capabilities=[MCP(url="https://..."), MCP(url="https://...")]

# 当前方案：环境变量
MCP_SERVERS=[{"name":"search","url":"https://..."},{"name":"train","url":"http://...","transport":"sse","default_args":{"api_key":"xxx"}}]
```

环境变量方式支持：
- 多环境部署（dev/staging/prod）不改代码
- K8s ConfigMap / Docker env 直接注入
- JSON 解析失败自动回退到 `MCP_SERVER_URL` 单端点
- 端点名称去重、缺失字段校验

### 4.8 生命周期管理

pydantic-deep 的 MCP Capability 生命周期绑定在 Agent 上，Agent 创建时连接，Agent 销毁时断开。每次请求创建新 Agent 就重新连接。

我们的生命周期独立于 Agent：

```
应用启动 → MCPClientManager.setup() → 创建 toolset 实例
         → ReasoningEngine.startup() → 预热资源缓存 + 启动刷新任务
每次请求 → get_toolsets() → 复用已有实例传入 Agent
定期/手动 → refresh() → 重建实例 + 清缓存
应用关闭 → shutdown() → 取消刷新任务
```

toolset 实例在请求间共享，不会每次请求都重新连接 MCP server。

## 5. 汇总对比

| 维度 | pydantic-deep MCP Capability | 当前方案 | 关系 |
|------|------------------------------|---------|------|
| 协议通信 | fastmcp transport | fastmcp transport | 完全复用 |
| 工具发现 & schema | FastMCPToolset | FastMCPToolset | 完全复用 |
| 命名空间 | PrefixTools | PrefixedToolset | 完全复用（同一个类） |
| 协议选择 | URL 路径推断 | 显式 transport 配置 + 推断兜底 | 增强 |
| 参数注入 | 不支持 | DefaultArgsToolset | 新增 |
| 缓存管理 | 无 | 两层缓存 + 定期/手动刷新 | 新增 |
| 配置管理 | 代码硬编码 | 环境变量 JSON 驱动 | 新增 |
| 生命周期 | 绑定 Agent | 独立于 Agent，请求间共享 | 新增 |
| 代码量 | ~3 行 | ~180 行（MCPClientManager + DefaultArgsToolset） | — |

## 6. 设计优势

### 对上透明，对下可控

LLM 视角完全无感 — 不管底层是 SSE 还是 Streamable，不管有没有 default_args，LLM 看到的就是一组标准的 function call 工具，带完整 JSON Schema，直接调用。不需要"先 search 再 call"的两步操作，不需要在 prompt 里塞工具列表文本，不需要理解 MCP 是什么。

运维视角完全可控 — 加端点、换协议、注入参数、调刷新频率，全部改环境变量，不动一行代码。

### 最小侵入，最大复用

整个方案只新增了两个组件：MCPClientManager（~100 行配置解析和生命周期管理）和 DefaultArgsToolset（~80 行参数注入包装器）。协议通信、工具发现、schema 转换、function calling 执行全部复用 pydantic-ai 和 fastmcp 原生实现。框架升级时，我们自动享受底层的 bug 修复和性能优化，不存在版本追赶的维护负担。

### 渐进式降级

- 不配 `MCP_SERVERS` → MCP 功能静默关闭，不影响其他工具
- 多端点中某个连接失败 → 跳过该端点，其余正常工作
- JSON 配置解析失败 → 自动回退到 `MCP_SERVER_URL` 单端点
- 不配 `transport` → fastmcp 自动推断，大多数场景够用
- 不配 `default_args` → 不包装 DefaultArgsToolset，零开销

每一层都有合理的默认行为，配置越少越简单，需要时再加。
