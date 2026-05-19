# 03. 开源深度分析计划

## 目标

已有 `doc-plugin/design/06-open-source-reference-and-reuse.md` 已经完成开源项目的初步参考矩阵。下一步需要从“设计参考”进入“模块级深度分析”。

深度分析不是泛泛介绍项目，而是回答以下问题：

- 这个项目可以解决我们哪个模块的问题。
- 它的架构是否适合企业 Agent 平台。
- 它能否直接复用、局部复用、fork，还是只能参考设计。
- 它的 license、安全、维护和二次开发风险是什么。
- 如果不复用代码，我们应该吸收哪些设计。

## 优先分析项目

| 优先级 | 项目 | 关联模块 | 分析目标 |
| --- | --- | --- | --- |
| P0 | Codex Plugins / openai/plugins / openai/codex | Manifest、package layout、marketplace、enable/disable、skills/MCP 组合 | 校验插件包结构和安装启用模型 |
| P0 | OpenAPI / Streamable HTTP MCP 相关实现 | OpenAPI connector、Streamable HTTP MCP | 先保证远程能力调用主链路跑通 |
| P1 | n8n | Credential schema、connector UX、连接测试 | 治理阶段再借鉴凭据模型和连接器体验 |
| P1 | mcpo | MCP Runtime / stdio adapter | stdio MCP 暂不考虑，仅后续需要时评估 |
| P1 | Dify plugin daemon | Runtime Host、debug runtime、serverless 思路 | 只在需要 Runtime Host 时深入；不作为第一阶段前置 |
| P1 | Open WebUI | MCP/OpenAPI/tools/pipelines 扩展分层 | 借鉴协议适配和扩展分层 |
| P1 | Claude Code | skills、MCP、hooks、subagents、settings、marketplace | 借鉴产品形态和能力组织，需要服务化改造 |
| P2 | ccpkg / Open Plugins | 能力包结构 | 辅助校验 package layout |
| P2 | LangChain / Flowise | tools、connector、workflow 产品形态 | 按具体模块需要补充调研 |

## 每个项目的分析模板

每个项目需要形成一份独立分析文档，建议结构如下：

```text
# 项目名称深度分析

## 结论先行

## 适用模块

## 架构和核心流程

## 可复用点

## 不适合直接复用的点

## License / 安全 / 维护风险

## 与当前 Plugin 设计的映射

## 建议动作
```

## 第一批分析文档

建议先补以下文档：

- `open-source-deep-dive/01-codex-plugins.md`
- `open-source-deep-dive/03-n8n-credential.md`
- `open-source-deep-dive/02-mcpo.md`
- `open-source-deep-dive/04-dify-plugin-daemon.md`
- `open-source-deep-dive/05-open-webui.md`
- `open-source-deep-dive/06-claude-code.md`

## 当前模块级复用结论

| 模块 | 推荐动作 | 说明 |
| --- | --- | --- |
| Manifest / Package Layout | 参考设计 | 参考 Codex Plugins、Dify、ccpkg，但 `plugin.yaml` 和企业字段自研 |
| Registry / Marketplace | 参考设计 + 自研实现 | 参考 Codex marketplace catalog，落地时结合内部制品仓库和 workspace 状态 |
| Plugin Manager | 自研 | 需要适配 workspace / agent / IAM / 公司管理后台 |
| Developer CLI | 自研为主 | 命令形态参考 Codex / ccpkg，schema、package、publish 逻辑按平台实现 |
| OpenAPI Runtime | 参考现有 tooling | 远程 HTTP 调用可用通用库，治理、凭据、审计和错误结构自研 |
| Streamable HTTP MCP | 按官方协议实现 | 以 MCP Streamable HTTP 规范为准；Open WebUI 仅作为产品边界参考 |
| Credential | 参考 n8n，生产接公司密钥系统 | 一期只保留 schema 和配置占位，后续再做 Broker |
| Admin Console | 自研 | 结合公司后台风格和 Plugin Manager API，不复用外部产品 UI |
| Runtime Host | 暂不采用 | Dify plugin daemon 仅作为后续需要本地/隔离执行时的设计参考 |

## 复用决策分级

| 等级 | 含义 | 示例 |
| --- | --- | --- |
| 直接复用 | 作为依赖引入，少量适配 | 需要非常谨慎，必须完成 license/security 评估 |
| 局部复用 / fork | 复用核心模块或协议适配器 | 仅在明确需要时评估，第一阶段不优先 |
| 设计参考 | 不引入代码，只吸收架构和产品体验 | Codex Plugins、Claude Code、n8n 多数能力更适合此类 |
| 不采用 | 不适合当前架构或成本过高 | 记录原因，避免反复讨论 |

## 阶段建议

第一阶段开发前必须完成：

- Codex Plugins / openai/plugins / openai/codex 深度分析。
- OpenAPI connector / Streamable HTTP MCP 的远程调用方案分析。

Credential、Policy、Audit、stdio MCP adapter 和 Runtime Host 都不阻塞第一阶段主链路。n8n、mcpo、Dify plugin daemon 可以放到后续治理或运行层阶段再深入。
