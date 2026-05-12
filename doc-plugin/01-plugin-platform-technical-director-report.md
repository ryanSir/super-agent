# Agent 平台 Plugin 能力规划与 POC 验证报告

## 1. 执行摘要

本报告围绕 Agent 平台的 Plugin 能力建设展开，目标是为公司内部不同业务 Agent 提供一套标准化、可治理、可扩展的能力接入机制。

当前 Agent 平台面临的问题不是“缺少某一个工具调用方式”，而是缺少一个统一机制来管理外部系统、数据源、工具、技能、凭据、权限、运行时和观测。如果继续由各业务 Agent 分别接入工具和系统，会带来重复建设、权限分散、凭据风险、审计缺失、运行隔离不足和长期维护成本上升。

本次工作形成了两个层面的交付：

1. **规划设计**：完成 Plugin 概念定义、能力模型、manifest 设计、运行时架构、MCP/OpenAPI 接入策略、开源参考、开发计划和端到端流程图。
2. **后端 POC**：完成一个可运行的 Plugin POC，验证插件从开发、校验、打包、发布、安装、启用、能力发现、权限凭据检查、统一调用、Runtime 执行、审计和事件记录的完整闭环。

核心结论如下：

- Plugin 应定义为 **可分发、可安装、可授权、可运行、可观测的 Agent 能力包**，而不是单一 API、单个 MCP server 或单个 tool。
- 业务 Agent 系统不应直接集成插件内部实现，而应通过 **Plugin 核心服务** 发现和调用插件能力。
- 第一版平台建议建设三类核心服务：**Plugin 核心服务、Plugin 管理平台、Plugin Runtime Host**。
- MCP 是 Plugin 支持的一种协议，不是 Plugin 本身；OpenAPI、Skill、Data Source、Tool 也都是 Plugin 内部可携带的能力类型。
- 当前 POC 代码没有直接复用开源项目代码，主要用于验证模块边界和端到端链路；生产化阶段应按模块评估自研、复用、fork 或接入公司已有系统。

## 2. 背景与建设必要性

随着业务 Agent 增多，平台需要持续接入更多外部能力，包括：

- 企业系统 API：Jira、Slack、飞书、CRM、内部业务系统。
- 数据源：知识库、数据库、文档、SaaS 数据。
- 工具协议：MCP server、OpenAPI connector。
- Agent 技能：领域任务流程、提示词约束、工具使用策略。
- 治理能力：凭据、权限、审计、观测、版本管理。

如果没有统一 Plugin 平台，各业务 Agent 会倾向于各自封装工具和系统接入，短期看灵活，长期会出现以下问题。

| 问题 | 表现 | 后果 |
| --- | --- | --- |
| 接入重复 | 多个团队重复封装同一 API、MCP 或数据源 | 研发浪费，行为不一致 |
| 凭据分散 | 各 Agent 自行管理 token、secret、OAuth 配置 | 泄露风险高，轮换困难 |
| 权限不统一 | 缺少 workspace、agent、user 级能力授权 | 越权调用和审计困难 |
| 观测缺失 | tool 调用、错误、耗时、成本没有统一记录 | 线上问题难定位 |
| 运行耦合 | 插件逻辑进入 Agent 主进程 | 插件异常可能影响 Agent 稳定性 |
| 生态不可持续 | 没有统一 package、manifest、registry | 插件无法复用、审核和版本治理 |

因此，Plugin 平台的价值不是增加一个“工具调用接口”，而是建设一个面向多业务 Agent 的能力中台。

## 3. 核心定义与边界

中文定义：

> Plugin 是一个声明式、可安装、可授权、可运行、可观测、可分发的 Agent 能力包，用于将外部系统、数据源、工具调用、技能流程或 UI 组件接入 Agent 平台。

英文定义：

> Plugin is a declarative, installable, permissioned, executable, observable and distributable capability package that extends the Agent Platform with external systems, data sources, tool invocations, skills, workflows and optional UI components.

概念边界如下：

| 概念 | 定位 | 说明 |
| --- | --- | --- |
| Plugin | 能力包、安装包、治理单元 | 负责分发、安装、授权、运行和治理 |
| Tool | 可被 Agent 调用的结构化函数 | 例如 `search_issues`、`send_message` |
| Skill | Agent 完成任务的方法和流程说明 | 更偏提示词、任务策略和工具组合方式 |
| MCP | 工具和数据能力的一种协议 | MCP 不是 Plugin 本身 |
| OpenAPI | 企业 API 接入方式之一 | 适合 REST API connector |
| Data Source | 查询或检索业务上下文 | 数据库、文档、知识库、SaaS 数据 |
| Credential | 认证和凭据声明 | 不应进入模型上下文 |
| Policy | 权限、敏感操作、人审、数据边界 | 平台治理能力 |
| App/UI | 配置页、操作面板、结果展示 | 第一版可后置 |

关键判断：

- Plugin 是治理和分发单元。
- Tool、Skill、MCP、OpenAPI、Data Source 是 Plugin 内部携带的能力类型。
- Agent Runtime 只应该看到被授权的能力描述、输入输出 schema 和调用结果，不应该直接接触密钥、内部网络细节和未授权数据。

## 4. 总体架构

端到端流程图如下：

![Plugin 端到端流程泳道图](./plugin-end-to-end-flow-swimlane.svg)

建议架构分为五类边界：

| 边界 | 责任方 | 说明 |
| --- | --- | --- |
| 业务 Agent 系统 | 各业务团队 | 已有或自行建设，后续通过 Plugin 核心服务对接插件能力 |
| Plugin 核心服务 | Plugin 平台团队 | 能力发现、权限、凭据、统一调用网关 |
| Plugin 管理平台 | Plugin 平台团队 | Registry、Manager、安装、启用、配置、版本和凭据管理 |
| Plugin Runtime Host | Plugin 平台团队 | 插件执行、MCP adapter、OpenAPI/Data Source/Skill runtime、运行隔离 |
| 外部系统 / 观测 | 复用现有系统 | MCP Server、企业 API、数据源、Langfuse |


1. **业务 Agent 系统是插件能力使用方**  
   各业务团队已有或自行建设业务 Agent，不需要把插件系统嵌进自己的 Agent 主进程。业务 Agent 通过 Plugin 核心服务获取能力并发起调用。

2. **Plugin 核心服务是平台治理和调用入口**  
   它负责 Capability Resolver、Policy Engine、Credential Broker 和 Tool Invocation Gateway，是业务 Agent 与插件 runtime 之间的稳定边界。

3. **Plugin Runtime Host 负责运行隔离**  
   插件执行不建议直接跑在业务 Agent 主进程内。Runtime Host 可以演进为 daemon、sidecar、container 或 remote runtime，以降低依赖冲突和故障扩散风险。

## 5. 管理面与调用面

Plugin 平台需要区分管理面和调用面。

### 5.1 管理面

管理面负责插件生命周期：

```text
Plugin SDK / CLI
  -> validate / package / publish
  -> Plugin Registry
  -> Plugin Manager
  -> install / enable / configure
  -> Capability Index
```

管理面核心职责：

- 插件创建、校验、打包、发布。
- 插件存储、版本、审核和 marketplace 展示。
- 插件安装、启用、禁用、升级、卸载。
- 插件配置、凭据绑定、workspace/agent 绑定。
- 插件能力索引生成。

### 5.2 调用面

调用面负责业务 Agent 调用插件能力：

```text
Business Agent
  -> Capability Resolver
  -> Policy Engine
  -> Credential Broker
  -> Tool Invocation Gateway
  -> Plugin Runtime Host
  -> MCP / OpenAPI / Data Source / Skill runtime
  -> Structured Result
  -> Audit / Events / Langfuse
```

调用面核心职责：

- 根据 workspace、agent、user 查询可用能力。
- 检查权限、敏感操作和数据边界。
- 校验或注入凭据，但不把凭据暴露给模型。
- 统一调用 MCP、OpenAPI、native tool、data source。
- 标准化结果和错误码。
- 记录审计、trace、latency、error、cost。

关键点：`Plugin Manager` 不应处在每次工具调用主链路上。它负责安装和启用阶段写入状态和能力索引；Agent 调用时由 Plugin 核心服务基于索引执行调用。

## 6. 端到端运行链路

完整链路如下：

```text
开发插件
  -> 编写 plugin.yaml / 子配置
  -> validate / package / publish
  -> Registry 存储插件包
  -> Plugin Manager 安装插件
  -> 启用并绑定 workspace / agent
  -> 生成 Capability Index
  -> 业务 Agent 发现可用能力
  -> 读取 Skill context
  -> Policy Engine 检查权限
  -> Credential Broker 校验/注入凭据
  -> Tool Invocation Gateway 统一调用
  -> Plugin Runtime Host 执行
  -> MCP / OpenAPI / Data Source / Skill runtime
  -> 返回结构化结果
  -> Audit / Events / Langfuse 观测
  -> Agent 生成最终回答
```

这条链路的设计目标是：

- 业务 Agent 面向能力编程，而不是面向插件实现编程。
- 平台统一管理凭据和权限，而不是让模型或业务 Agent 直接接触密钥。
- 插件运行和 Agent 主进程解耦，避免插件故障影响 Agent 稳定性。
- 所有能力调用都有统一审计和观测入口。

## 7. 能力模型与 manifest

第一版建议支持以下能力：

| 能力类型 | 第一版建议 | 说明 |
| --- | --- | --- |
| Tool Plugin | 支持 | 结构化函数调用 |
| API Connector Plugin | 支持 | 基于 OpenAPI/REST 接入企业系统 |
| MCP Plugin | 支持 | 优先 Streamable HTTP；stdio 通过 adapter |
| Skill Plugin | 支持 | 封装领域任务流程和 Agent 使用说明 |
| Data Source Plugin | 支持 | 接入知识库、数据库、文档、SaaS 数据 |
| Credential Plugin | 支持 | 声明认证方式、配置表单、凭据测试 |
| Workflow Plugin | 二期 | 多步骤自动化流程 |
| Trigger Plugin | 二期 | 外部事件触发 Agent 或 workflow |
| App/UI Plugin | 二期 | 插件配置页、操作面板、结果展示 |
| Agent Strategy Plugin | 暂不纳入 | 容易与 Skill 混淆，且影响 Agent Runtime 核心机制 |

manifest 建议采用：

```text
plugin.yaml + plugin.schema.json
```

原因：

- `plugin.yaml` 对开发者更友好。
- `plugin.schema.json` 便于严格校验、IDE 提示和平台兼容控制。
- 复杂插件可通过 `path` 引用 tools、skills、credentials、openapi、data_sources、mcp 子配置。

示例结构：

```text
plugin-package.zip
├── plugin.yaml
├── README.md
├── checksums.json
├── skills/
├── tools/
├── openapi/
├── credentials/
├── data_sources/
├── mcp/
├── runtime/
└── tests/
```

## 8. POC 完成情况

当前后端 POC 已完成 11 个阶段，并已按未来服务边界重构代码。

| 阶段 | 能力 | 当前实现 |
| --- | --- | --- |
| Phase 1 | 插件规范、校验、打包、发布 | `developer_tooling/` |
| Phase 2 | 安装、启用、Capability Index | `management/` |
| Phase 3 | 统一调用网关 | `core/gateway.py` |
| Phase 4 | 凭据、权限、审计 | `core/credentials.py`、`core/policy.py`、`core/audit.py` |
| Phase 5 | OpenAPI Runtime | `runtimes/openapi_runtime.py`，当前为 mock runtime |
| Phase 6 | Streamable HTTP MCP Runtime | `runtimes/mcp_runtime.py`，已用真实 stage MCP endpoint 验证 |
| Phase 7 | Skill Runtime | `runtimes/skill_runtime.py` |
| Phase 8 | Data Source Runtime | `runtimes/data_source_runtime.py` |
| Phase 9 | Runtime Host / stdio adapter PoC | `runtime_host/host.py` |
| Phase 10 | Runtime Events / Timeout | `core/observability.py` |
| Phase 11 | E2E 验收 | `acceptance/e2e.py` |

代码分层：

```text
plugin_poc/
├── developer_tooling/   # 开发侧 SDK / CLI
├── management/          # Plugin 管理平台
├── core/                # Plugin 核心服务
├── runtime_host/        # Plugin Runtime Host
├── runtimes/            # MCP / OpenAPI / Data Source / Skill runtime
├── acceptance/          # E2E 验收
└── shared/              # 共享基础能力
```

这说明 POC 不只是功能验证，也验证了未来服务拆分边界。

## 9. POC 验收结果

一键验收命令：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli run-e2e \
  --plugin-dir plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-e2e-registry \
  --state /tmp/plugin-poc-e2e-state
```

验收内容：

- 发布插件到 Registry。
- 从 Registry 安装插件。
- 启用插件并绑定 `workspace + agent`。
- 配置凭据。
- 启动 Runtime Host 状态。
- 调用 tool capability。
- 调用 data source capability。
- 渲染 skill context。
- 检查 runtime health。

当前结果：

```text
ruff check plugin-poc: passed
pytest: 45 passed, 1 warning
run-e2e: status ok
```

真实 MCP 验证：

```text
https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw?APP_ID=Patsnap
```

已验证：

- `tools/list` 能解析 `text/event-stream` JSON-RPC 返回。
- `tools/call` 能通过 Plugin gateway 调用真实 MCP tool。
- 调用结果能通过统一结构返回。
- 调用链路能记录 audit。

## 10. POC 证明了什么

当前 POC 证明了以下关键判断：

| 判断 | POC 证据 |
| --- | --- |
| Plugin 可以作为能力包管理 | `plugin.yaml`、package、registry、install、enable 已跑通 |
| 能力可以被 workspace/agent 绑定 | Capability Index 已支持 scoped capability |
| Agent 调用可以统一走 Gateway | tool、openapi、mcp、data source 均通过 `invoke` 入口 |
| 权限和凭据可以前置治理 | `policy.py`、`credentials.py` 已接入调用链路 |
| Skill 可以作为 Agent 上下文 | `render-skill-context` 已可渲染 SKILL.md |
| Streamable MCP 可接入 | 已使用真实 stage MCP endpoint 验证 |
| Runtime Host 应独立抽象 | 已有 start/stop/health 和 stdio adapter metadata |
| 审计和观测需要成为调用链路一部分 | audit log、runtime events 已写入 |

当前 POC 是模块边界验证，不是生产实现。它的价值是降低后续技术选型和服务化改造的不确定性。

## 11. 开源参考与复用判断

本次设计参考了以下项目：

| 项目 | 参考价值 | 当前判断 |
| --- | --- | --- |
| OpenAI Codex Plugins | plugin package、skills/MCP/apps/hooks/assets、marketplace | 强设计参考 |
| openai/codex | plugin marketplace、安装、启用、cache、配置加载 | 源码级实现参考 |
| openai/plugins | 官方 plugin 示例 | package layout 和 manifest 示例参考 |
| Dify plugin daemon | runtime、生命周期、debug、serverless 思路 | 重点源码调研 |
| Open WebUI | MCP/OpenAPI/tools/pipelines 扩展分层 | 设计参考 |
| mcpo | MCP-to-OpenAPI adapter | 候选复用或 fork |
| n8n | credential schema、连接测试、connector UX | 设计参考 |
| ccpkg / Open Plugins | 能力包结构 | 设计参考 |

Codex Plugins 对我们的设计是强校验：

| Codex Plugins | 我们的设计 |
| --- | --- |
| `.codex-plugin/plugin.json` | `plugin.yaml + plugin.schema.json` |
| `skills/` | Skill Plugin |
| `.mcp.json` / MCP servers | MCP Runtime |
| `.app.json` / apps | 后续 App/UI Plugin |
| `hooks/` | 后续 lifecycle hooks / trigger / workflow |
| `assets/` | marketplace / Admin Console 展示素材 |
| marketplace JSON catalog | Plugin Registry / Marketplace |
| enable / disable plugin | workspace/agent 级启用禁用 |

当前 POC 代码没有直接复制或引入这些开源项目代码，是自研最小实现。

后续生产化不是把 POC 整体替换为某个开源框架，而是按模块评估：

| POC 模块 | 后续可能动作 |
| --- | --- |
| Manifest / package layout | 参考 Codex Plugins、Dify、ccpkg 优化字段和目录结构 |
| Registry / Marketplace | 参考 Codex marketplace，结合内部制品仓库实现 |
| Plugin Manager | 大概率自研，因为要适配公司 workspace/agent/IAM |
| MCP Runtime / stdio adapter | 重点评估 `mcpo`、Open WebUI、Codex MCP 配置模型 |
| Runtime Host | 参考 Dify plugin daemon，但不一定直接复用 |
| Credential | 参考 n8n schema，实现大概率自研并接公司密钥系统 |
| Policy | 自研或接公司权限系统 |
| OpenAPI Runtime | 可参考现有 OpenAPI tooling，但企业治理部分自研 |
| Skill Runtime | 参考 Codex Skills / Plugins，核心实现较轻 |
| Observability | 接入现有 Langfuse |
| Admin Console | 自研，结合公司后台框架 |

## 12. 技术选型建议

### 12.1 Runtime 形态

候选形态：

| 形态 | 优点 | 风险 | 建议 |
| --- | --- | --- | --- |
| In-process | 实现简单、低延迟 | 隔离差，插件异常影响 Agent | 不建议 |
| Local daemon | 适合 stdio MCP、本地调试、生命周期集中管理 | 需要管理进程和资源 | 第一版 PoC 重点方向 |
| Sidecar | 就近部署，隔离更好 | 部署复杂，资源占用高 | 二期评估 |
| Remote service | 适合已有企业 API/MCP 服务 | 依赖网络和服务稳定性 | 第一版支持 |
| Container runtime | 隔离强，资源限制清晰 | 编排和安全扫描复杂 | 二期/三期 |
| Serverless runtime | 弹性好 | 冷启动和状态管理复杂 | 后续评估 |

建议第一版采用：

```text
Remote service runtime + Local daemon PoC
```

原因：

- Streamable HTTP MCP 和 OpenAPI connector 可以优先走 remote service。
- stdio MCP、本地调试和内部插件托管可通过 daemon 验证。
- 避免插件直接进入业务 Agent 主进程。

### 12.2 MCP / OpenAPI 策略

建议 MCP 和 OpenAPI 并存：

- MCP 适合 agent-native tool 协议，尤其是工具发现和交互。
- OpenAPI 适合企业 API connector，便于治理、文档化、operation allowlist 和审计。
- 对 stdio MCP，可以评估 `mcpo` 或自研 adapter，将其转成 HTTP/OpenAPI 或 Streamable HTTP。

第一版优先：

- Streamable HTTP MCP。
- OpenAPI connector。
- stdio MCP adapter PoC。

### 12.3 Observability

不建议自研完整观测平台。建议：

- Plugin 核心服务记录 audit 和 runtime events。
- trace、tool call、latency、error、cost 接入现有 Langfuse。
- 敏感字段需要脱敏和权限控制。

## 13. 当前 POC 边界

当前 POC 已能证明主链路可行，但不是生产版：

- Registry 是本地文件目录，不是正式制品仓库或 marketplace。
- Plugin Manager 状态是 JSON 文件，不是数据库。
- OpenAPI Runtime 是 mock runtime，还没有真实 HTTP 请求和凭据注入。
- stdio MCP adapter 只登记 metadata，没有真正启动子进程做代理。
- Credential 只做字段校验和脱敏展示，没有加密存储。
- Policy 是最小规则，没有接入公司 IAM / RBAC / ABAC。
- Runtime Host 是生命周期状态模型，没有进程、容器或 sidecar 隔离。
- Observability 写本地 JSONL，还没有接入 Langfuse。
- Admin Console 未实现。
- 业务 Agent 对接目前用 CLI 模拟，没有提供 HTTP API / SDK。

这些边界不影响 POC 结论。它们是下一阶段生产化的工作范围。

## 14. 风险与技术关注点

| 风险 | 影响 | 建议 |
| --- | --- | --- |
| stdio MCP 托管复杂 | Runtime Host 复杂度上升 | 第一版优先 Streamable HTTP，stdio 通过 adapter PoC 验证后再生产化 |
| 插件隔离不足 | 插件异常影响平台稳定性 | Runtime Host 独立部署，后续评估 sidecar / container |
| 凭据泄露 | 高安全风险 | Credential Broker 注入，凭据不进入模型上下文，生产化接密钥系统 |
| 权限后补困难 | 架构返工 | 第一版即纳入 workspace/agent/user 权限模型 |
| OpenAPI tool 质量不稳定 | Agent 调用效果差 | 支持 operation allowlist 和人工描述增强 |
| Registry 重复建设 | 交付周期变长 | 优先评估复用内部制品仓库 |
| Admin Console 被低估 | 影响落地体验 | MVP 只做安装、配置、启用、日志核心页面 |
| 开源复用 license 不清 | 法务和安全风险 | 进入实现前做 license/security 检查 |
| 多业务 Agent 接入方式不统一 | 推广成本高 | 提供标准 Discovery / Invocation / Skill Context API 和 SDK |

## 15. 生产化 Roadmap

### M1：服务化改造

- 将 CLI 能力拆成 HTTP API。
- 建设 Plugin 核心服务。
- 建设 Plugin 管理平台后端。
- 使用数据库保存 plugin、version、install、enable、capability、credential、audit 状态。

### M2：Registry 和包治理

- 接入内部制品仓库或建设内部 Plugin Registry。
- 增加 plugin package 签名、checksum 校验、版本状态、审核状态。
- 增加 plugin schema 版本兼容策略。
- 支持 marketplace catalog 和 curated plugin list。

### M3：真实 Runtime

- OpenAPI Runtime 支持真实 HTTP 调用、凭据注入、错误归一、超时重试。
- MCP Runtime 支持 Streamable HTTP、stdio adapter、session 管理。
- Runtime Host 支持 daemon / sidecar 部署形态。
- 增加插件级资源隔离和运行健康检查。

### M4：安全治理

- 凭据加密存储。
- 接入公司 IAM / RBAC / ABAC。
- 支持 workspace、agent、user 级授权。
- 敏感操作人审和操作审计。

### M5：业务 Agent 对接

- 提供 Capability Discovery API。
- 提供 Tool Invocation API。
- 提供 Skill Context API。
- 给业务团队提供 SDK 或接入示例。

### M6：观测和管理后台

- 接入 Langfuse 或现有观测平台。
- 建设 Admin Console：插件列表、详情、安装、启用、凭据配置、日志查看。
- 增加调用 trace、latency、error、cost、audit 查询。

## 16. MVP 范围建议

第一版 MVP 建议包含：

- `plugin.yaml + plugin.schema.json`
- zip package
- internal Plugin Registry
- Plugin Manager
- Capability Index
- Plugin 核心服务
- Tool Invocation Gateway
- Credential Broker
- Policy Engine
- Audit Log
- Streamable HTTP MCP Runtime
- OpenAPI Runtime
- Skill Runtime
- Data Source Runtime
- Runtime Host daemon PoC
- Langfuse 接入
- 最小 Admin Console
- 2-3 个官方示例插件

第一版建议暂不包含：

- 外部开放 marketplace
- 插件商业化结算
- 完整 App/UI Plugin 沙箱
- 完整 Workflow / Trigger 系统
- Agent Strategy Plugin
- Model Provider Plugin
- 完整 serverless runtime
- 复杂灰度发布和多版本并行治理

## 17. 资源与协作建议

推荐团队配置：

| 角色 | 建议人数 | 主要职责 |
| --- | --- | --- |
| Tech Lead / 架构 | 1 | 总体架构、关键技术选型、评审和风险收敛 |
| 后端 / 平台工程 | 3-4 | Registry、Manager、Core、Runtime、Credential、Policy |
| 前端工程 | 1-2 | Admin Console、插件配置、凭据表单、日志页面 |
| QA / 测试 | 1 | E2E、权限、异常、回归测试 |
| DevOps / SRE | 0.5-1 | Runtime 部署、日志、监控、资源隔离 |
| 安全工程 | 0.5 | 凭据、权限、审计、安全评估 |

粗略节奏：

```text
M0：技术选型和 PoC 结论
M1：manifest、package、registry 初版
M2：install/enable、Capability Index 跑通
M3：OpenAPI/MCP 调用链路跑通
M4：Credential、Policy、Audit、Admin Console 初版
M5：示例插件端到端验收，MVP release candidate
```

## 18. 建议决策点

建议在评审中确认以下问题：

1. Plugin 是否作为 Agent 平台正式能力方向推进。
2. 是否认可 `Plugin 核心服务 + Plugin 管理平台 + Plugin Runtime Host` 的服务边界。
3. 业务 Agent 对接方式：HTTP API、SDK，还是统一网关协议。
4. Registry 是否复用内部制品仓库。
5. Runtime Host 第一版选择 daemon、sidecar 还是 remote runtime。
6. stdio MCP 是否第一版必须生产支持。
7. Credential 是否接入公司密钥系统，OAuth2 refresh 是否第一版必须支持。
8. Policy 是否接入现有 IAM / RBAC / ABAC。
9. Observability 是否直接接入 Langfuse。
10. Admin Console 是否进入 MVP 范围。
11. 第一批官方插件选型：建议至少包含一个 OpenAPI connector、一个 MCP plugin、一个 Skill/Data Source plugin。

## 19. 建议汇报讲解路径

如果按技术评审方式讲解，建议顺序如下：

1. 先讲背景问题：为什么各业务 Agent 不能各自接工具。
2. 再讲核心定义：Plugin 是能力包，不是 MCP 或 API。
3. 讲架构图：业务 Agent、Plugin 核心服务、管理平台、Runtime Host 的边界。
4. 讲端到端流程：从开发发布到 Agent 调用。
5. 讲 POC：11 个阶段、代码分层、E2E 和真实 MCP 验证。
6. 讲开源参考：Codex 是强背书，Dify/mcpo/n8n 是实现参考。
7. 讲边界和风险：哪些 POC 已证明，哪些还没生产化。
8. 讲 Roadmap 和需要决策的问题。

## 20. 附录：关键文档

- [Plugin 能力规划草案](./02-plugin-capability-plan.md)
- [Plugin 端到端流程说明](./03-plugin-end-to-end-flow.md)
- [Plugin Runtime 架构](./design/03-runtime-architecture.md)
- [MCP / OpenAPI 接入策略](./design/04-mcp-openapi-strategy.md)
- [开源项目参考与复用策略](./design/06-open-source-reference-and-reuse.md)
- [0-1 开发计划与粗估](./design/07-development-plan-and-estimation.md)
- [POC 验收说明与后续 Roadmap](./04-poc-acceptance-and-roadmap.md)
- [POC 代码分层与部署映射](./05-code-structure-and-deployment-mapping.md)
