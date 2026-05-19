# 05. Open WebUI 深度分析

## 结论先行

Open WebUI 适合作为 MCP、OpenAPI、Tools、Pipelines 多扩展形态的设计参考，重点看扩展分层和协议适配体验。不建议直接作为 Plugin 平台核心依赖。

第一阶段口径调整：

- MCP 不考虑 stdio adapter。
- 第一阶段只考虑远程 Streamable HTTP MCP endpoint。
- Open WebUI 仍可作为 MCP / OpenAPI 扩展分层参考，但不作为第一阶段依赖。
- Streamable HTTP MCP 的实现以 MCP 官方 Transport 规范为准：客户端通过 HTTP POST 向单一 MCP endpoint 发送 JSON-RPC 消息，响应可为 JSON 或 SSE。

## 适用模块

- MCP / OpenAPI 接入策略。
- Tools 分层。
- Pipeline / Workflow 参考。
- 管理和配置体验参考。

## 需要重点分析的问题

- MCP server 如何配置和暴露给模型。
- OpenAPI tools 如何导入、选择和调用。
- Tools 与 Pipelines 的边界如何划分。
- 权限和配置作用域如何管理。
- 是否有可借鉴的 adapter、schema 或调用封装。

## 可复用点

- MCP 和 OpenAPI 扩展分层。
- 工具配置和调用体验。
- 协议适配设计。

## 不适合直接复用的点

- Open WebUI 是完整产品，不是企业 Plugin 核心服务框架。
- 多租户、公司 IAM、凭据隔离和审计要按当前平台重建。

## 建议动作

- 作为 P1 设计参考。
- 第一阶段不抽取 Open WebUI adapter。
- 重点对齐 MCP / OpenAPI / Tools 的边界划分。
- 若后续进入 stdio MCP 或复杂 MCP server 管理，再重新评估 Open WebUI / mcpo / Dify daemon。

## 参考来源

- [Model Context Protocol - Transports](https://modelcontextprotocol.io/specification/draft/basic/transports)
