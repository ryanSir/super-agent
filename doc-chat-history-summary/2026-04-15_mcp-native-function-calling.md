# 对话摘要：MCP原生调用改造

> 保存时间：2026-04-15
> 原始轮次：~60 轮

## 背景

将 MCP 工具从"元工具间接调用"（tool_search + call_mcp_tool）改为 pydantic-ai 原生 function calling，同时支持 SSE 和 Streamable HTTP 双协议，解决参数无 JSON Schema 约束、代码维护量大的问题。

## 核心内容

- 对比了 5 种方案（保持现状 / 自建 Tool 包装 / pydantic-deep 原生 / MCPServerHTTP+SSE / FastMCPToolset），最终选择 FastMCPToolset
- MCPServerSSE 已 deprecated，FastMCPToolset 是更现代的替代，支持 URL 自动推断协议
- fastmcp 的"自动推断"基于 URL 路径模式匹配（`/sse` 关键词），不是运行时探测。纯 SSE 服务且 URL 不含 `/sse` 的必须显式配 `"transport": "sse"`
- 实测验证：智慧芽 eureka_claw（Streamable HTTP）自动推断成功，同程火车票（SSE）需显式指定
- 发现 pydantic-deep 的 `patch_tool_calls`（默认 True）与 MCP toolset 错误处理冲突，导致重复 tool_result → Anthropic 400。设置 `patch_tool_calls=False` 解决
- 实现了 `DefaultArgsToolset` 包装器，支持端点级 `default_args` 自动注入固定参数（如 api_key），同时从工具 schema 中隐藏这些字段，对 LLM 完全透明

## 产出物

- `openspec/changes/mcp-native-function-calling/` — 完整 change（proposal + design + specs + tasks，17/17 完成）
- `src_deepagent/capabilities/mcp/client_manager.py` — 重写，FastMCPToolset + DefaultArgsToolset + 双协议支持
- `src_deepagent/capabilities/mcp/deferred_registry.py` — 已删除
- `src_deepagent/capabilities/base_tools.py` — 移除 tool_search、call_mcp_tool
- `src_deepagent/capabilities/registry.py` — 改用 mcp_client_manager.get_toolsets()
- `src_deepagent/context/builder.py` — 移除 deferred_tool_names 参数和 MCP prompt 注入
- `src_deepagent/orchestrator/reasoning_engine.py` — MCP 资源改为 mcp_toolsets
- `src_deepagent/orchestrator/agent_factory.py` — 传入 toolsets + patch_tool_calls=False
- `src_deepagent/context/templates/tool_usage.md` — 移除 tool_search 说明
- `src_deepagent/gateway/rest_api.py` — 清理 call_mcp_tool 相关引用
- `.env` — MCP_SERVERS 配置新增 transport 和 default_args
- `function-compare-summary/2026-04-15_mcp-native-function-calling.md` — 方案对比文档

## 后续事项

- `src_deepagent/README.md` 中仍有旧的 DeferredToolRegistry / tool_search 描述，需同步更新
- 工具数量膨胀（50+）时全量注入 toolsets 的 token 开销待观察
- `patch_tool_calls=False` 可能影响 pydantic-deep 其他工具的错误修复能力，需持续观察
