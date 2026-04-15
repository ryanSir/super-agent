# MCP 工具调用方式改造 — 方案对比与决策

> 整理时间：2026-04-15
> 对话背景：将 MCP 工具从"元工具间接调用"改为原生 function calling，同时支持 SSE 和 Streamable HTTP 双协议

## 背景与目标

当前 MCP 工具通过 `tool_search` + `call_mcp_tool` 两个"元工具"间接调用，LLM 实际执行的是 `call_mcp_tool(tool_name="xxx", arguments={...})`，参数是自由 dict，缺乏 JSON Schema 约束，参数准确率低。同时只支持 Streamable HTTP 传输协议，部分未改造的 MCP 服务（SSE 协议）无法接入。目标是让 MCP 工具以原生 function calling 方式调用，并兼容 SSE/Streamable 双协议。

## 方案对比

| 方案 | 核心思路 | 优点 | 缺点/风险 |
|------|---------|------|----------|
| 方案 A：保持现状（元工具间接调用） | `tool_search` 获取 schema → `call_mcp_tool` 执行 | 渐进式加载节省 prompt token（工具 50+ 时有意义） | 参数无 schema 约束；400+ 行自维护代码；间接调用增加复杂度 |
| 方案 B：自建 Tool 包装 | MCPClientManager 发现工具后，手动包装为 `pydantic_ai.Tool` 对象 | 保留自建连接管理；LLM 直接 function calling 带 schema | 需要手动构造 Tool 闭包；pydantic-ai Tool 不直接接受 raw JSON schema |
| 方案 C：pydantic-deep 原生 MCP capability | 直接用 `MCP(url=...)` 传入 `create_deep_agent(capabilities=...)` | 代码量最少（~10 行）；框架全托管 | 丢失自建连接管理的灵活性（多端点、定期刷新、原子替换） |
| 方案 D：pydantic-ai MCPServerHTTP/MCPServerSSE | 用 `MCPServerHTTP` / `MCPServerSSE` 作为 toolsets 传入 Agent | 原生 function calling；保留自建连接管理层 | `MCPServerSSE` 已标记 deprecated |
| 方案 E：FastMCPToolset（最终选择） | 用 `FastMCPToolset` 作为 toolsets，URL 自动推断协议，需要时显式传 transport | 不依赖 deprecated API；URL 自动推断；`.prefixed()` 命名空间隔离；有 headers 时传 transport 对象 | 不支持 Sampling 和 Elicitation（当前不需要） |

## 决策结论

**选择：方案 E — FastMCPToolset**

## 决策理由

- pydantic-ai 的 `MCPServerSSE` 已 deprecated，`FastMCPToolset` 是更现代的替代
- `FastMCPToolset` 传 URL 可自动推断协议（基于 URL 路径是否含 `/sse`），API 更简洁
- `.prefixed(name)` 一行实现命名空间隔离，替代自建前缀逻辑
- 有 headers 时可传 `SSETransport` / `StreamableHttpTransport` 对象，灵活性不丢
- 保留了自建 `MCPClientManager` 管理层（多端点配置解析、定期刷新、容错降级）
- 当前场景不需要 Sampling 和 Elicitation，FastMCPToolset 的限制不影响

## 关键发现

### fastmcp 自动推断协议的实际行为

fastmcp 的"自动推断"是基于 URL 路径模式匹配（`/sse` 关键词），不是运行时协议探测：

```python
# fastmcp 源码逻辑
if re.search(r"/sse(/|\?|&|$)", path):
    return "sse"
else:
    return "http"  # 默认 Streamable HTTP
```

- URL 路径含 `/sse` → 自动推断为 SSE（如 `http://example.com/sse`）
- URL 路径不含 `/sse` 但实际是 SSE 协议 → 推断失败（405 Method Not Allowed）
- 结论：纯 SSE 服务且 URL 不含 `/sse` 的，必须显式配置 `"transport": "sse"`

### 实测验证

| 服务 | 协议 | 自动推断 | 工具数 |
|------|------|---------|--------|
| 智慧芽 eureka_claw | Streamable HTTP | 成功 | 33 |
| 同程火车票 trainmcpserver | SSE | 失败（需显式指定） | 1 |

## 遗留问题

- `src_deepagent/README.md` 中仍有旧的 `DeferredToolRegistry` / `tool_search` 描述，需同步更新文档
- 工具数量膨胀场景（50+）下全量注入 toolsets 的 token 开销待观察，必要时可在 MCPClientManager 层做白名单过滤
