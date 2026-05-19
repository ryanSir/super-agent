# 02. mcpo 深度分析

## 结论先行

`mcpo` 是 MCP-to-OpenAPI adapter 的候选参考，适合用于验证 stdio MCP 如何转成 HTTP / OpenAPI 风格入口。但当前第一阶段 MCP 只考虑 Streamable HTTP，不考虑 stdio MCP adapter，因此 `mcpo` 不再作为 P0 调研项。

## 适用模块

- 后续 stdio MCP adapter。
- 后续 MCP-to-HTTP / OpenAPI 桥接。
- Tool Invocation Gateway 的协议适配层。

## 需要重点分析的问题

- 如何启动和管理 stdio MCP server。
- MCP tools 如何映射成 OpenAPI operations。
- 输入输出 schema 如何转换。
- 错误、超时、进程退出如何表达。
- 是否支持多 server、多 session、多租户隔离。
- 是否方便接入凭据注入、审计和 trace。

## 可复用点

- MCP-to-HTTP / OpenAPI adapter 思路。
- stdio MCP server 启动和协议桥接逻辑。
- schema 转换逻辑。

## 不适合直接复用的点

- 如果缺少多租户、权限、凭据和审计边界，不能直接进入生产主链路。
- 如果进程管理和资源隔离不满足公司要求，只能作为 PoC 或设计参考。

## 建议动作

- 暂不作为第一阶段阻塞项。
- 只有当后续明确需要 stdio MCP 托管时，再做源码级 spike。
- 届时再给出“直接依赖 / fork / 自研 adapter”的明确建议。
