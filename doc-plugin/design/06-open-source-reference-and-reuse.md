# 06. 开源项目参考与复用策略

## 目标

本文件用于说明 Plugin 系统参考哪些开源项目、借鉴哪些设计、哪些代码可能复用、哪些只适合作为设计参考，以及后续是否需要源码级调研。

当前结论：

> 规划阶段不需要把所有开源项目源码逐行读完；但对准备复用、fork 或深度集成的项目，必须做源码级 spike 和 license/security 评估。

当前 `plugin-poc` 代码是自研最小实现，主要用于验证模块边界和端到端链路，没有直接复制或引入 Dify、Codex、Open WebUI、mcpo、n8n 等项目代码。

后续生产化也不建议把 POC 整体替换为某个开源框架，而应按模块评估：

| 当前 POC 模块 | 后续可能动作 |
| --- | --- |
| Manifest / package layout | 参考 Codex Plugins、Dify、ccpkg 优化字段和目录结构 |
| Registry / Marketplace | 参考 Codex marketplace，结合内部制品仓库实现 |
| Plugin Manager | 大概率自研，因为要适配公司 workspace/agent/IAM |
| MCP Runtime / stdio adapter | 重点评估 `mcpo`、Open WebUI、Codex MCP 配置模型 |
| Runtime Host | 参考 Dify plugin daemon，但不一定直接复用 |
| Credential | 参考 n8n schema，实现大概率自研并接公司密钥系统 |
| Policy | 大概率自研或接公司权限系统 |
| OpenAPI Runtime | 可参考现有 OpenAPI tooling，但企业治理部分自研 |
| Skill Runtime | 参考 Codex Skills / Plugins，核心实现较轻 |
| Data Source Runtime | 根据公司数据源、知识库和权限体系自研或接入现有数据平台 |
| Observability | 接入现有 Langfuse，而不是自研完整观测系统 |
| Admin Console | 自研，结合公司后台框架 |

## 开源项目参考矩阵

| 项目 | 参考价值 | 可能复用范围 | 当前建议 |
| --- | --- | --- | --- |
| Dify plugin daemon | 插件生命周期、runtime、调试模式、serverless 思路 | daemon/runtime 设计、生命周期模型、部分接口思路 | 重点源码调研，谨慎复用代码 |
| OpenAI Codex Plugins | plugin 作为 skills、MCP、apps/connectors、hooks、assets 的组合包；manifest、marketplace、安装策略 | package layout、manifest 字段、marketplace metadata、repo/personal marketplace 思路 | 强设计参考，尤其适合校验我们的能力包方向 |
| openai/codex | Codex CLI / 本地 agent 的开源实现，包含 plugin marketplace、安装、启用、配置加载等线索 | marketplace 解析、本地 cache、enable/disable 状态、插件加载流程 | 源码级调研，作为实现参考，不直接整体复用 |
| openai/plugins | 官方 Codex plugin 示例集合 | plugin package layout、真实 manifest、skills/MCP/app/hooks/assets 示例 | 示例参考，可抽取最佳实践 |
| openai/codex-plugin-cc | 官方跨工具插件示例，把 Codex 接入 Claude Code | 真实 plugin 产品体验、命令组织、安装调用体验 | 产品体验和结构参考 |
| Claude Code | skills、MCP、slash commands、hooks、subagents、LSP、monitors、settings、plugin marketplace 的组合扩展模型 | 能力组织、配置分层、权限体验、hooks/subagents/monitors 形态 | 强产品形态参考，需要服务化改造 |
| Open WebUI | MCP、OpenAPI、Tools、Pipelines 多扩展形态 | 扩展分层、协议适配、产品体验 | 设计参考为主 |
| mcpo | MCP-to-OpenAPI adapter | PoC、adapter 思路、局部复用或 fork | 优先源码调研和 PoC |
| n8n | connector、credential、节点市场、API 集成体验 | credential schema、连接测试、连接器 UX | 设计参考为主 |
| Open Plugins / ccpkg | 能力包结构、skills/MCP/hooks/agents 打包 | package layout、manifest 组织方式 | 设计参考为主 |
| LangChain | tool schema、tool execution、integration ecosystem | tool 抽象、部分 connector 生态 | 按需复用 |
| Flowise | 可视化节点、Agent/workflow 编排 | 产品形态、节点参数设计 | 不作为核心依赖 |

## 是否需要仔细阅读源码

需要分层处理，不能所有项目都同等深度阅读。

### 第一层：设计参考

只需要阅读文档、架构说明、示例和少量关键代码。

适用项目：

- Open WebUI
- OpenAI Codex Plugins
- openai/plugins
- openai/codex-plugin-cc
- Claude Code
- n8n
- Open Plugins / ccpkg
- Flowise

目标：

- 看清概念模型。
- 看清用户体验。
- 看清目录结构和 manifest 组织方式。
- 看清哪些设计适合借鉴，哪些不适合。

### 第二层：实现参考

需要阅读核心模块源码，但不一定直接复用。

适用项目：

- openai/codex
- Dify plugin daemon
- LangChain tools/integrations

目标：

- 看清 runtime 生命周期。
- 看清 plugin invocation 协议。
- 看清错误处理、日志、调试模式。
- 看清依赖管理和部署方式。
- 判断是否能局部复用或重写。

### 第三层：候选复用

需要源码级 spike、license 检查、安全评估和 PoC。

适用项目：

- mcpo
- Dify plugin daemon 的局部模块或协议思路

目标：

- 跑通最小样例。
- 判断是否能嵌入公司平台。
- 判断是否满足多租户、安全、审计、部署要求。
- 判断维护成本和二次开发成本。

## 复用判断标准

每个开源项目进入实现复用前，需要检查：

| 维度 | 需要回答的问题 |
| --- | --- |
| License | 是否允许商用、修改、分发、闭源集成 |
| 架构匹配 | 是否适合当前 Agent 平台架构 |
| 多租户 | 是否支持 tenant/workspace/user 隔离 |
| 安全 | 是否有凭据隔离、权限边界、输入输出校验 |
| 可观测 | 是否方便接入日志、trace、审计 |
| 可维护 | 项目是否活跃，代码结构是否清晰 |
| 可裁剪 | 是否能局部使用，而不是整体绑定 |
| 部署 | 是否适合公司基础设施和运行环境 |
| 性能 | 是否能满足并发、延迟和资源要求 |
| 社区风险 | 是否存在频繁 breaking changes 或维护不确定性 |

## 推荐调研顺序

第一优先级：

1. `mcpo`：验证 MCP-to-OpenAPI adapter 是否能作为 stdio MCP 接入桥。
2. `dify-plugin-daemon`：调研 plugin runtime、生命周期、debug runtime、serverless runtime。
3. `OpenAI Codex Plugins / openai/plugins / openai/codex`：校验 plugin package、marketplace、skills/MCP/apps/hooks 组合模型，并调研 Codex plugin 加载和 enable/disable 实现。

第二优先级：

4. `n8n`：调研 credential schema、连接测试和 connector 开发体验。
5. `Open WebUI`：调研 MCP/OpenAPI/tools/pipelines 的扩展分层。

第三优先级：

6. `Open Plugins / ccpkg`：调研 package layout 和能力打包方式。
7. `LangChain`：按具体 connector/tool 场景调研。
8. `Flowise`：作为产品形态和节点编排参考。

## OpenAI Codex Plugins 对我们的校验

OpenAI Codex 的 plugin 文档进一步证明了我们当前设计方向是合理的：plugin 更适合作为一个可分发的能力包，而不是单一工具协议。

相关开源资源：

| 仓库 | 定位 | 对我们的价值 |
| --- | --- | --- |
| `openai/codex` | Codex CLI / 本地 agent 开源实现 | 看 plugin marketplace 解析、安装 cache、enable/disable、配置加载等实现方式 |
| `openai/plugins` | 官方 Codex plugin 示例集合 | 看真实 plugin 目录结构、manifest、skills、MCP、apps、hooks、assets 如何组织 |
| `openai/codex-plugin-cc` | Codex for Claude Code 官方插件 | 看跨工具 plugin 的产品化体验、命令组织和安装调用方式 |

Codex 的设计要点：

- plugin 有必需 manifest：`.codex-plugin/plugin.json`。
- plugin 可以打包 `skills/`、`.mcp.json`、`.app.json`、`hooks/`、`assets/`。
- marketplace 是一个 JSON catalog，可以面向 repo、个人或官方目录。
- marketplace entry 包含 source、install policy、auth policy、category 等信息。
- 安装后 Codex 会把 plugin 放入本地 cache，并可单独 enable / disable。

与我们当前设计的对应关系：

| Codex Plugins | 我们的设计 |
| --- | --- |
| `.codex-plugin/plugin.json` | `plugin.yaml + plugin.schema.json` |
| `skills` | Skill Plugin / `SKILL.md` |
| `mcpServers` / `.mcp.json` | MCP Runtime / MCP Plugin |
| `apps` / `.app.json` | App/UI Plugin 或 API Connector 的后续扩展 |
| `hooks` | 后续 lifecycle hooks / trigger / workflow |
| `assets` | marketplace / admin console 展示素材 |
| marketplace JSON catalog | Plugin Registry / Marketplace |
| install policy / auth policy | Plugin Manager / Policy / Credential |
| enable / disable plugin | workspace/agent 级启用和禁用 |

关键差异：

- Codex 面向 Codex 客户端和开发者本地/团队分发，偏客户端安装模型。
- 我们面向企业 Agent 平台，偏服务化治理，需要多租户、workspace/agent 绑定、凭据隔离、审计、Langfuse 观测和 Runtime Host。
- Codex 的 marketplace 可以作为我们 Registry/Marketplace 的产品形态参考，但我们需要额外建设 Plugin 核心服务和 Runtime Host。
- Codex 目前公开的是产品实现、规范文档和示例仓库，不是一个可直接嵌入企业平台的独立 plugin runtime framework。

建议吸收进后续设计：

- manifest 增加 `interface` 元数据，用于 Admin Console / marketplace 展示。
- Registry 增加 marketplace catalog 概念，支持 curated list。
- package layout 保留 `skills/`、`assets/`、`mcp/`、`hooks/` 等目录的标准位置。
- 增加 install policy、auth policy、category 等 marketplace 字段。

## Claude Code 对我们的校验

Claude Code 的扩展体系进一步证明：Agent 插件体系不应只围绕 MCP 或 API connector 设计，而应支持多能力组合。

相关官方资料：

| 资料 | 对我们的价值 |
| --- | --- |
| Claude Code overview | 理解 Claude Code 作为本地 agentic coding tool 的运行边界 |
| Claude Code settings | 参考项目级、用户级、托管级配置分层 |
| Claude Code MCP | 参考 MCP server 配置和工具接入体验 |
| Claude Code slash commands | 参考显式命令入口和可复用工作流入口 |
| Claude Code hooks | 参考工具调用前后、提示词提交、会话结束等生命周期事件 |
| Claude Code subagents | 参考专用 Agent 模板、工具权限和独立上下文模型 |
| Claude Code LSP / monitors | 参考代码智能和后台事件监听能力 |
| Claude Code plugin marketplace | 参考插件发现、安装和分发体验 |

与我们当前设计的对应关系：

| Claude Code | 我们的设计 |
| --- | --- |
| Skills | Skill Plugin / Skill Context API |
| MCP servers | MCP Plugin / MCP Runtime |
| Slash commands | 二期 Command Plugin / Workflow entry |
| Hooks | 二期 lifecycle hook / trigger / policy event |
| Subagents | 二期 Agent Template / Team Agent 参考，MVP 不纳入 |
| LSP servers | 二期 Code Intelligence 能力参考 |
| Background monitors | 二期 Trigger / Event Source / Runtime worker 参考 |
| Settings / permissions | Plugin Manager config + Policy Engine |
| Plugin marketplace | Plugin Registry / Marketplace |

关键差异：

- Claude Code 是本地 CLI 和项目工作区模型，配置和执行都靠本地 Agent Runtime 承担。
- 我们是企业 Agent 平台模型，需要服务端多租户治理、workspace/agent 绑定、凭据隔离、审计和观测。
- Claude Code 的 hooks 可以作为生命周期事件参考，但不能直接照搬任意脚本执行模式。
- Claude Code 的 subagents 能力强，但企业权限和成本边界复杂，第一版不建议纳入 Plugin MVP。
- Claude Code 的 LSP 和 monitors 有参考价值，但涉及长驻进程、资源限制和事件治理，不建议进入 MVP。

建议吸收进后续设计：

- manifest 预留 `commands`、`hooks`、`agents`、`monitors`、`lsp` 扩展字段，但 MVP 不急于实现。
- Skill 继续保持轻量上下文能力，不进入 Runtime Host。
- Runtime Host 聚焦 stdio MCP、本地代码插件、受控 hook、monitors 和长任务 worker。
- Plugin 管理平台吸收 Claude Code 的配置分层思路，映射到 tenant/workspace/agent/user 作用域。

详见：[Claude Code 插件机制分析](./08-claude-code-plugin-analysis.md)。

## PoC 建议

建议做 3 个短 PoC：

### PoC 1：MCP-to-OpenAPI Adapter

目标：

- 使用 mcpo 或类似方案把一个 stdio MCP server 暴露为 HTTP/OpenAPI。
- 平台通过 Tool Gateway 调用。
- 验证 tool schema、调用结果、错误处理和超时。

成功标准：

- Agent 可以发现并调用 MCP tool。
- 调用链路可以记录 audit log。
- 凭据不进入模型上下文。

### PoC 2：Dify-style Runtime Host

目标：

- 验证 local runtime / debug runtime / remote runtime 的抽象是否适合公司平台。
- 明确 Plugin Runtime Host 与 Agent Runtime 的通信协议。

成功标准：

- 插件可以被启动、停止、调用。
- 插件异常不会影响 Agent 主进程。
- 调用日志和错误可以被平台收集。

### PoC 3：Credential Schema

目标：

- 参考 n8n 设计 credential schema。
- 自动生成配置表单。
- 支持 test connection。

成功标准：

- 一个 OpenAPI connector 可以声明凭据。
- 用户配置后能测试连接。
- 调用时由 Credential Broker 注入凭据。

## 参考来源

- [Dify Plugin Manifest][dify-plugin-manifest]
- [dify-plugin-daemon][dify-plugin-daemon]
- [OpenAI Codex Build Plugins][openai-codex-build-plugins]
- [openai/codex][openai-codex]
- [openai/plugins][openai-plugins]
- [openai/codex-plugin-cc][openai-codex-plugin-cc]
- [Open WebUI Extensibility][open-webui-extensibility]
- [Open WebUI MCP][open-webui-mcp]
- [mcpo][mcpo]
- [Open Plugins][open-plugins]
- [ccpkg][ccpkg]
- [n8n Integrations][n8n-integrations]

[dify-plugin-manifest]: https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest
[dify-plugin-daemon]: https://github.com/langgenius/dify-plugin-daemon
[openai-codex-build-plugins]: https://developers.openai.com/codex/plugins/build
[openai-codex]: https://github.com/openai/codex
[openai-plugins]: https://github.com/openai/plugins
[openai-codex-plugin-cc]: https://github.com/openai/codex-plugin-cc
[open-webui-extensibility]: https://docs.openwebui.com/features/extensibility/
[open-webui-mcp]: https://docs.openwebui.com/features/extensibility/mcp/
[mcpo]: https://github.com/open-webui/mcpo
[open-plugins]: https://open-plugins.com/
[ccpkg]: https://ccpkg.dev/
[n8n-integrations]: https://docs.n8n.io/integrations/
