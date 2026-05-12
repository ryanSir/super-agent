# 04. MCP / OpenAPI 接入策略

## 目标

Plugin 系统需要同时支持 MCP 和 API/OpenAPI 接入。两者不是互斥关系，而是面向不同场景的能力入口。

本文件定义：

- MCP 和 OpenAPI 在 Plugin 系统中的定位。
- Agent 平台内部如何统一抽象。
- stdio、Streamable HTTP、HTTP+SSE 的处理策略。
- MCP-to-OpenAPI adapter 的使用边界。

## 基本判断

平台内部统一抽象为 **Tool Invocation**，外部接入同时支持 MCP 和 OpenAPI。

```text
Agent Runtime
   ↓
Tool Invocation Gateway
   ├── MCP Runtime
   ├── OpenAPI Runtime
   ├── Native Tool Runtime
   └── Data Source Runtime
```

MCP 适合接入已有工具生态和标准 MCP server。OpenAPI/API 适合企业系统集成、网关治理、审计、配额、错误码和 SDK 化接入。

## 协议选择

| 场景 | 推荐协议 |
| --- | --- |
| 企业系统 API | OpenAPI 优先 |
| 已有 MCP server | MCP 接入 |
| 新开发 MCP server | Streamable HTTP 优先 |
| stdio MCP | 通过 mcpo-like adapter 转 Streamable HTTP 或 OpenAPI |
| 老版 HTTP+SSE MCP | 作为兼容项支持，不作为新插件优先协议 |
| 浏览器多租户平台 | 避免直接管理 stdio |
| 需要审计、配额、网关 | OpenAPI 更成熟 |
| 需要生态兼容 | MCP 更方便 |

## MCP 接入策略

MCP 当前优先支持：

- `Streamable HTTP`
- `stdio`

老版 `HTTP+SSE` 可以作为兼容项支持，但不作为新插件的优先协议。

建议架构：

```text
MCP Server
   │
   ├── Streamable HTTP ──────▶ MCP Runtime
   │
   ├── HTTP+SSE ─────────────▶ MCP Runtime (legacy)
   │
   └── stdio MCP ─▶ MCP Adapter ─▶ Streamable HTTP / OpenAPI
                                                │
                                                ▼
                                        Tool Gateway
```

第一版建议：

- 支持 Streamable HTTP MCP。
- 支持 OpenAPI ingestion。
- 兼容老版 HTTP+SSE MCP，但不作为新插件优先协议。
- stdio MCP 不直接暴露给多租户 Web Runtime，而是通过 adapter。
- 平台内部统一做权限、审计、credential 注入。

## OpenAPI 接入策略

OpenAPI 适合作为企业 API connector 的主要接入协议。

OpenAPI Runtime 需要支持：

- 解析 OpenAPI spec。
- 生成 tool schema。
- 支持 operation allowlist。
- 支持参数 schema 校验。
- 支持凭据注入。
- 支持错误码归一。
- 支持调用日志和审计。
- 支持 rate limit 和 timeout。

对于只需要 API 接入的插件，可以支持 manifest-only 或 OpenAPI-only 模式：

```text
plugin.yaml
openapi/service.yaml
credentials/oauth.yaml
```

这种模式可以减少插件开发成本，不要求开发者写 runtime 代码。

## MCP-to-OpenAPI Adapter

mcpo 的 MCP-to-OpenAPI adapter 思路值得参考，可用于降低 MCP 工具接入和平台统一治理的复杂度。

适用场景：

- 已有 stdio MCP server，但平台希望统一走 HTTP 调用。
- 平台希望复用 OpenAPI 网关、审计、限流、鉴权能力。
- 多租户环境不希望直接在 Agent Runtime 中管理 stdio 子进程。

需要注意：

- Adapter 不应绕过平台权限模型。
- Adapter 需要处理工具 schema、错误、流式输出和超时。
- Adapter 需要明确凭据注入边界。
- Adapter 应作为 PoC 优先验证项，而不是默认强依赖。

