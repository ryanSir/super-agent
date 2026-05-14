# Agent 平台 Plugin 能力规划与 POC 验证报告

## 1. 背景执行摘要

本报告围绕 Agent 平台的 Plugin 能力建设展开，目标是为公司内部不同业务 Agent 提供一套标准化、可治理、可扩展的能力接入机制。

Plugin 为 Agent 平台提供了一种标准化的能力包机制。它将 Skill、Tool、MCP、OpenAPI、Data Source、Credential、Policy 和 Runtime 配置封装为可分发、可安装、可启用、可授权、可调用、可观测的能力包，让业务 Agent 可以面向能力编程。

通过 Plugin 机制，平台可以统一复用外部能力、集中管理凭据和权限、标准化工具调用结果、隔离插件运行环境，并沉淀统一的审计和观测链路，从而提升多业务 Agent 的扩展效率、安全性和长期可维护性。

本次工作形成了两个层面的交付：

1. **规划设计**：完成 Plugin 概念定义、能力模型、manifest 设计（结构化声明文件）、运行时架构、MCP/OpenAPI 接入策略、开源参考、开发计划和端到端流程图。
2. **后端 POC**：完成一个可运行的 Plugin POC，验证插件从开发、校验、打包、发布、安装、启用、能力发现、权限凭据检查、统一调用、Runtime 执行、审计和事件记录的完整闭环。

## 2. 核心定义与边界

中文定义：

> Plugin 是一个声明式、可安装、可授权、可运行、可观测、可分发的 Agent 能力包，用于将外部系统、数据源、工具调用、技能流程或 UI 组件接入 Agent 平台。

英文定义：

> Plugin is a declarative, installable, permissioned, executable, observable and distributable capability package that extends the Agent Platform with external systems, data sources, tool invocations, skills, workflows and optional UI components.

Plugin 与其他组件的关系：

Plugin 是 Tool、Skill、MCP、OpenAPI 等能力之上的组织和治理单元。Tool 关注一个函数怎么被调用，Skill 关注 Agent 如何完成一类任务，MCP 关注工具和上下文如何通过协议暴露，OpenAPI 关注 REST API 如何被描述和接入。Plugin 关注的是这些能力如何作为一个完整资产被声明、打包、分发、安装、授权、配置、调用、运行和观测。

因此，Plugin 更像一个能力容器和交付边界。一个 Plugin 可以只包含一种能力，例如只封装一个 MCP server；也可以组合多种能力，例如同时包含 OpenAPI 工具、Skill 使用说明、Credential 配置、权限策略和结果展示 UI。业务 Agent 使用的是 Plugin 暴露出的已授权能力，而不是直接依赖插件内部的协议、密钥、代码结构或运行方式。

Agent、Plugin 和 Skill 的区别可以放在一起看。Agent 是任务执行和决策主体，负责理解用户目标、规划步骤、选择能力并生成结果。Plugin 是能力资产和治理边界，负责把某一组外部能力、使用说明、凭据、权限和运行方式标准化地提供给 Agent。Skill 是任务方法和行为指导，负责告诉 Agent 面对某类任务时应该遵循什么步骤、约束、判断标准和工具使用策略。

也就是说，Agent 面向任务闭环，Plugin 面向能力交付，Skill 面向任务执行方法。三者可以组合使用：一个“研发助手 Agent”可以安装 Jira Plugin、GitLab Plugin 和文档检索 Plugin，同时加载代码审查 Skill。Agent 决定什么时候查 Jira、什么时候看代码、什么时候总结风险；Plugin 负责把 Jira、GitLab、文档检索等能力以受控、可复用、可审计的方式提供出来；Skill 则指导 Agent 如何做代码审查、如何判断风险、如何组织输出。因此，Agent 可以组合多个 Plugin 和 Skill，一个 Plugin 或 Skill 也可以被多个 Agent 复用。

Plugin 的主要作用：

1. **能力打包**：把 Tool、Skill、MCP、OpenAPI、Data Source、Credential、Policy、UI 配置等相关内容组织在一个插件包中，而不是散落在不同 Agent 项目里。
2. **生命周期管理**：支持插件的创建、校验、打包、发布、安装、启用、禁用、升级和卸载，让能力可以像平台资产一样被管理。
3. **权限与凭据治理**：统一声明插件需要什么权限、依赖什么凭据、可被哪些 workspace、agent、user 使用，避免业务 Agent 或模型直接接触密钥。
4. **能力发现与调用入口**：把插件内的能力注册到 Capability Index，业务 Agent 只看到被授权的能力描述、schema 和调用入口，不需要理解插件内部实现。
5. **运行隔离与协议适配**：对需要执行环境的能力提供 Runtime Host、adapter 或 remote runtime，隔离依赖冲突、进程异常和网络访问细节。
6. **审计与观测**：统一记录安装、启用、调用、错误、耗时、成本和审计事件，便于排障、安全追踪和后续治理。
7. **复用与生态建设**：让一个插件可以服务多个业务 Agent，沉淀公司级能力资产，而不是每个团队重复封装同一套外部系统。

概念边界如下：

| 概念 | 定位 | 说明 |
| --- | --- | --- |
| Agent | 任务执行和决策主体 | 负责理解目标、规划步骤、选择能力、调用工具并生成结果 |
| Plugin | 能力包、安装包、治理单元 | 负责把多种能力统一打包、发布、安装、授权、配置、运行和观测 |
| Tool | 可被 Agent 调用的结构化函数 | 解决“调用什么函数”的问题，例如 `search_issues`、`send_message` |
| Skill | Agent 完成任务的方法和流程说明 | 解决“Agent 如何使用能力完成任务”的问题，更偏提示词、步骤、约束和工具组合策略 |
| MCP | 工具和数据能力的一种协议 | 解决“如何暴露工具和上下文”的协议问题，MCP server 可以被 Plugin 封装和治理 |
| OpenAPI | 企业 API 接入方式之一 | 解决“如何接入 REST API”的问题，适合 API connector 类型插件 |
| Data Source | 查询或检索业务上下文 | 解决“从哪里获取上下文”的问题，例如数据库、文档、知识库、SaaS 数据 |
| Credential | 认证和凭据声明 | 解决“如何认证和注入密钥”的问题，不应进入模型上下文 |
| Policy | 权限、敏感操作、人审、数据边界 | 解决“谁能用、能用到什么程度、是否需要审批”的治理问题 |
| App/UI | 配置页、操作面板、结果展示 | 解决“如何配置和展示”的交互问题，第一版可后置 |

Plugin 和 Skill 的区别尤其需要明确：

| 维度 | Plugin | Skill |
| --- | --- | --- |
| 核心定位 | 平台级能力包和治理单元 | Agent 级任务方法和使用说明 |
| 解决问题 | 能力如何交付、安装、授权、配置、调用、运行和观测 | Agent 面对某类任务时应该按什么流程、约束和策略执行 |
| 内容形态 | 可以包含 Tool、Skill、MCP、OpenAPI、Data Source、Credential、Policy、UI、Runtime 配置 | 通常是说明文档、提示词片段、步骤流程、工具使用策略和少量资源 |
| 是否执行 | Plugin 本身不是单个执行函数，但可以携带需要执行的 tool、connector 或 runtime | Skill 通常不直接执行，更像 Agent 的上下文和行为指导 |
| 管理粒度 | workspace / agent / user 级安装、启用、授权和版本管理 | 通常随 Agent 或 Plugin 分发，用于影响 Agent 行为 |
| 举例 | Jira Plugin：包含 Jira API tool、OAuth 凭据、权限策略、issue 查询 skill、配置页 | “如何分析 Jira issue 并总结风险”的 Skill |

一个直观例子：

- 如果只做一个 `search_issues` Tool，Agent 只能调用这个函数，但平台不知道它如何安装、谁能用、凭据从哪里来、调用是否需要审计。
- 如果只写一个 Jira 分析 Skill，Agent 知道如何分析 issue，但它未必具备访问 Jira 的 API、凭据和权限。
- 如果做成 Jira Plugin，则可以同时包含 Jira API 工具、OAuth 配置、权限策略、issue 分析 Skill、调用审计和版本管理。业务 Agent 安装并获得授权后，就能用一整套受治理的 Jira 能力。

## 3. 总体架构

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

## 4. 管理面与调用面

Plugin 平台需要区分管理面和调用面。

它们与上一节五类边界的对应关系如下：

| 平面 | 主要对应边界 | 参与边界 | 说明 |
| --- | --- | --- | --- |
| 管理面 | Plugin 管理平台 | Plugin 核心服务、Plugin Runtime Host、外部系统 / 观测 | 负责插件从开发、发布、安装、启用、配置到能力索引生成的生命周期管理 |
| 调用面 | Plugin 核心服务 | 业务 Agent 系统、Plugin Runtime Host、外部系统 / 观测 | 负责业务 Agent 在运行时发现、授权、调用插件能力，并记录审计和观测 |

其中，`Plugin 管理平台` 是管理面的主体，`Plugin 核心服务` 是调用面的主体。`Plugin Runtime Host` 不是单独的第三个平面，也不建议作为 `Plugin 核心服务` 进程内的一个普通模块实现；它是被管理面纳入生命周期管理、被调用面按需调度执行的独立运行边界。`业务 Agent 系统` 是调用面的发起方，`外部系统 / 观测` 是管理面和调用面共同依赖的外部边界。

### 4.1 管理面

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

### 4.2 调用面

调用面负责业务 Agent 调用插件能力：

```text
Business Agent
  -> Capability Resolver
  -> Policy Engine
  -> Credential Broker
  -> Tool Invocation Gateway
  -> 按能力类型分流
     -> Skill Context API
     -> Remote MCP / OpenAPI / Data Source runtime
     -> Plugin Runtime Host for stdio MCP / local tool / isolated runtime
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

### 4.3 Runtime Host 的适用范围

`Plugin Runtime Host` 不是业务 Agent 的编排层，也不是所有插件能力的必经执行路径。它的定位是插件执行宿主，用来处理需要平台托管、协议适配、生命周期管理或运行隔离的能力。

从服务边界看，Runtime Host 不应直接内嵌在 Plugin 核心服务里。Plugin 核心服务负责能力发现、权限检查、凭据注入、调用路由和审计记录；Runtime Host 负责真正拉起、托管或适配需要运行环境的插件能力。两者可以在 POC 阶段放在同一代码仓库、甚至用同一个进程模拟，但生产化时建议拆成独立服务、daemon、sidecar、container worker 或 remote runtime，避免插件依赖、资源消耗和运行异常影响核心调用网关。

不同能力的处理方式如下：

| 能力类型 | 第一版建议处理方式 | 是否必须经过 Runtime Host | 说明 |
| --- | --- | --- | --- |
| Skill | Plugin 核心服务提供 Skill Context API，业务 Agent 拼入 system prompt 或 agent context | 否 | Skill 主要是任务流程、提示词约束和工具使用策略，不是典型执行型 runtime |
| OpenAPI / REST API | Plugin 核心服务通过 Gateway 调用 remote service runtime | 否 | 重点是权限、凭据注入、operation allowlist、错误归一和审计 |
| Streamable HTTP MCP | Plugin 核心服务通过 Gateway 调用远程 MCP endpoint | 否 | MCP 服务本身已经是可访问的远程服务，平台主要做治理和调用封装 |
| stdio MCP | Runtime Host 拉起或托管 stdio MCP，并通过 adapter 暴露为 HTTP 或平台内部协议 | 是 | stdio 需要进程管理、协议转换、健康检查和日志采集 |
| Data Source | 视数据源类型决定，优先通过 remote connector 或核心服务封装 | 视情况 | 远程数据源可直接走 Gateway；本地索引、私有连接器或需要隔离的查询执行可走 Runtime Host |
| Native Tool / 本地代码插件 | Runtime Host 托管插件进程、worker、容器或 sidecar | 是 | 需要处理依赖冲突、资源限制、超时取消和故障隔离 |
| Workflow / Trigger | 后续按执行复杂度评估 | 视情况 | 简单触发可由管理面和核心服务处理，长任务或事件 worker 更适合独立 runtime |

因此，第一版可以采用较轻的 Runtime Host 策略：

- Skill 不进入 Runtime Host，只作为 Agent 上下文能力暴露。
- OpenAPI 和 Streamable HTTP MCP 优先走 remote service runtime，由 Plugin 核心服务统一治理和调用。
- stdio MCP、本地插件、需要隔离的 native tool 再进入 Runtime Host。
- Runtime Host 第一版可以先保留生命周期、health、adapter metadata 和 daemon PoC，不必一开始实现完整容器化运行平台。

## 5. 端到端链路

完整链路需要拆成两个阶段：插件准备链路和 Agent 运行时调用链路。前者发生在开发、发布和安装阶段，后者发生在业务 Agent 真正处理用户请求时。

插件准备链路如下：

```text
开发插件
  -> 编写 plugin.yaml / 子配置
  -> validate / package / publish
  -> Registry 存储插件包
  -> Plugin Manager 安装插件
  -> 启用并绑定 workspace / agent
  -> 生成 Capability Index
```

Agent 运行时调用链路如下：

```text
用户请求进入业务 Agent
  -> 业务 Agent 查询或加载可用能力
  -> 按能力类型读取 Skill context 或发起 tool/data 调用
  -> Policy Engine 检查权限
  -> Credential Broker 校验/注入凭据
  -> Tool Invocation Gateway 统一调用
  -> 按能力类型分流执行
     -> Skill Context API 返回 Agent 上下文
     -> Remote MCP / OpenAPI / Data Source runtime 执行远程调用
     -> Plugin Runtime Host 执行 stdio MCP / local tool / isolated runtime
  -> 返回结构化结果
  -> Audit / Events / Langfuse 观测
  -> Agent 生成最终回答
```

这两段链路的设计目标是：

- 业务 Agent 面向能力编程，而不是面向插件实现编程。
- 平台统一管理凭据和权限，而不是让模型或业务 Agent 直接接触密钥。
- 插件运行和 Agent 主进程解耦，避免插件故障影响 Agent 稳定性。
- 所有能力调用都有统一审计和观测入口。

## 6. 能力模型与 manifest

第一版建议支持以下能力：

| 能力类型 | 第一版建议 | 说明 |
| --- | --- | --- |
| Tool Plugin | 支持 | 结构化函数调用 |
| API Connector Plugin | 支持 | 基于 OpenAPI/REST 接入企业系统 |
| MCP Plugin | 支持 | 优先 Streamable HTTP；stdio 通过 adapter |
| Skill Plugin | 支持 | 封装领域任务流程和 Agent 使用说明 |
| Data Source Plugin | 支持 | 接入知识库、数据库、文档、SaaS 数据 |
| Credential Plugin | 支持 | 声明认证方式、配置表单、凭据测试 |
| Workflow Plugin | 待定 | 多步骤自动化流程 |
| Trigger Plugin | 待定 | 外部事件触发 Agent 或 workflow |
| App/UI Plugin | 待定 | 插件配置页、操作面板、结果展示 |
| Agent Strategy Plugin | 待定 | 容易与 Skill 混淆，且影响 Agent Runtime 核心机制 |

后置能力说明：

| 能力类型 | 具体含义 | 示例 | 为什么不放 MVP |
| --- | --- | --- | --- |
| Workflow Plugin | 插件内置一段可执行的多步骤流程，不只是提供单个 tool 或 skill | “创建 Jira issue -> 通知 Slack -> 写入周报文档” | 需要状态管理、失败重试、补偿、长任务调度，复杂度高于普通工具调用 |
| Trigger Plugin | 插件可以响应外部事件，主动触发 Agent 或 workflow，而不是等用户请求时再调用 | GitLab merge request 创建后触发代码审查 Agent；CRM 客户状态变化后触发跟进流程 | 需要事件订阅、鉴权、去重、限流、回放和安全隔离，容易扩大平台边界 |
| App/UI Plugin | 插件提供配置页、操作面板或结果展示组件 | Jira Plugin 提供 OAuth 配置页、项目选择器、issue 详情展示卡片 | 需要前端扩展框架、权限控制、组件沙箱和发布审核，第一版可以先用平台通用配置页替代 |
| Agent Strategy Plugin | 插件试图改变 Agent 的整体规划、记忆、工具选择或多 Agent 协作策略 | “让 Agent 按某种 ReAct / Plan-and-Execute / 多子 Agent 策略运行” | 会深入影响 Agent Runtime 核心行为，边界容易和 Skill、Agent Template 混淆，暂不建议开放 |

第一版建议把重点放在“能力接入和治理”：Tool、API Connector、MCP、Skill、Data Source、Credential。Workflow、Trigger、App/UI 和 Agent Strategy 暂不承诺具体阶段，后续需要结合业务场景、平台边界和实现成本单独评估。

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

## 7. POC 完成情况

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

## 8. POC 验收结果

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

## 9. POC 证明了什么

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

## 10. 开源参考与复用判断

本次设计参考了以下项目：

| 项目 | 参考价值 | 当前判断 |
| --- | --- | --- |
| OpenAI Codex Plugins | plugin package、skills/MCP/apps/hooks/assets、marketplace | 强设计参考 |
| openai/codex | plugin marketplace、安装、启用、cache、配置加载 | 源码级实现参考 |
| openai/plugins | 官方 plugin 示例 | package layout 和 manifest 示例参考 |
| Claude Code | skills、MCP、slash commands、hooks、subagents、LSP、monitors、settings、plugin marketplace | 强产品形态参考，需服务化改造 |
| Dify plugin daemon | runtime、生命周期、debug、serverless 思路 | 重点源码调研 |
| Open WebUI | MCP/OpenAPI/tools/pipelines 扩展分层 | 设计参考 |
| mcpo | MCP-to-OpenAPI adapter | 候选复用或 fork |
| n8n | credential schema、连接测试、connector UX | 设计参考 |
| ccpkg / Open Plugins | 能力包结构 | 设计参考 |

Codex Plugins 和 Claude Code 对我们的设计形成了交叉校验：

| 能力 / 机制 | Codex Plugins 参考 | Claude Code 参考 | 我们的设计判断 |
| --- | --- | --- | --- |
| 插件声明 | `.codex-plugin/plugin.json` | marketplace / settings 中的扩展配置 | 采用 `plugin.yaml + plugin.schema.json`，兼顾可读性和结构化校验 |
| Skill | `skills/` | skills | Skill 是 Agent 上下文和任务方法说明，可作为 Plugin 内能力分发，不必须进入 Runtime Host |
| MCP | `.mcp.json` / MCP servers | MCP servers | MCP 是 Plugin 支持的协议能力之一，远程 MCP 走 Gateway，stdio MCP 走 Runtime Host |
| App/UI | `.app.json` / apps | 部分客户端交互和配置能力 | App/UI Plugin 暂定，后续评估配置页、操作面板和结果展示组件 |
| Hooks / Trigger | `hooks/` | hooks、monitors | 可作为 lifecycle hooks、trigger 或 workflow 的参考，但不在 MVP 中承诺 |
| 子 Agent / 策略 | 无直接核心映射 | subagents、Agent 协作策略 | 更接近 Agent Runtime 或 Agent Template 议题，不建议第一版作为 Plugin 开放 |
| Code Intelligence | 无直接核心映射 | LSP、monitors | 可作为代码类 Agent 的专门能力参考，暂不纳入通用 Plugin MVP |
| 静态素材 | `assets/` | marketplace 展示信息 | 用于 Plugin Registry、Marketplace 和 Admin Console 展示 |
| 市场和安装 | marketplace JSON catalog、enable / disable | plugin marketplace | 对应 Plugin Registry / Marketplace，以及 workspace/agent 级安装、启用、禁用 |

结论是：Codex Plugins 更直接验证了 package layout、manifest、marketplace、enable/disable 等插件工程形态；Claude Code 更完整展示了本地 Agent 客户端如何组合 skills、MCP、hooks、subagents、LSP、monitors、settings 和 marketplace。两者都支持一个判断：Plugin 应是多能力组合包，而不是单一 MCP server、单一 API connector 或单段 Skill。

同时，Claude Code 偏本地 CLI 和项目目录配置；我们的平台需要把同类能力服务化，落到 Plugin 核心服务、管理平台、Policy、Credential、Gateway、Runtime Host 和 Admin Console。

详见：[Claude Code 插件机制分析](./design/08-claude-code-plugin-analysis.md)。

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

## 11. 技术选型建议

### 11.1 整体选型原则

第 10 节已经按模块给出了开源参考和复用判断，本节不再重复模块清单。技术选型的核心原则是：Plugin 平台的企业治理能力应以自研或接入公司现有系统为主，开源项目主要用于校验设计、复用局部 adapter 或借鉴产品体验。

具体口径如下：

1. **治理主链路优先自研或接公司系统**  
   Plugin Manager、Policy、Credential、Capability Index、Invocation Gateway 需要适配公司 workspace、agent、user、IAM、密钥系统和审计要求，不适合直接套用外部框架。

2. **协议和适配层优先参考或局部复用开源**  
   MCP adapter、OpenAPI connector、manifest/package layout、marketplace metadata 可以参考 Codex Plugins、Open WebUI、mcpo、Dify、ccpkg 等项目。若进入代码复用，需要先做 license、安全和维护成本评估。

3. **开发者体验和产品形态参考成熟产品**  
   Codex Plugins、Claude Code、n8n 对插件目录结构、marketplace、凭据配置、连接测试、enable/disable、skills/MCP 组合方式有参考价值，但需要服务化改造，不能直接照搬本地客户端模型。

4. **运行执行能力先按需建设**  
   OpenAPI、Streamable HTTP MCP 和远程数据源优先走 Plugin 核心服务统一治理和调用。stdio MCP、本地代码插件、长任务 worker、hook 等需要托管执行的能力后续再按真实需求评估，不把完整 Runtime Host 作为第一阶段前置条件。

5. **观测和后台优先接现有基础设施**  
   Observability 不建议自研完整平台，优先接 Langfuse 或公司现有 trace/audit/log 系统；Admin Console 优先基于公司后台框架实现。

因此，第一阶段选型重点不是“选一个开源框架替换 POC”，而是明确哪些模块必须自研、哪些模块参考开源设计、哪些模块可能局部复用、哪些模块可以接公司已有基础设施。

### 11.2 MCP / OpenAPI 策略

建议 MCP 和 OpenAPI 并存：

- MCP 适合 agent-native tool 协议，尤其是工具发现和交互。
- OpenAPI 适合企业 API connector，便于治理、文档化、operation allowlist 和审计。
- 对 stdio MCP，可以评估 `mcpo` 或自研 adapter，将其转成 HTTP/OpenAPI 或 Streamable HTTP。

第一版优先：

- Streamable HTTP MCP。
- OpenAPI connector。
- stdio MCP adapter PoC。

### 11.3 Observability

不建议自研完整观测平台。建议：

- Plugin 核心服务记录 audit 和 runtime events。
- trace、tool call、latency、error、cost 接入现有 Langfuse。
- 敏感字段需要脱敏和权限控制。

## 12. 当前 POC 边界

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

## 13. 风险与技术关注点

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

## 14. 生产化 Roadmap

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

## 15. MVP 范围建议

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

## 16. 资源与协作建议

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

## 17. 建议决策点

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


## 18. 附录：关键文档

- [Plugin 能力规划草案](./02-plugin-capability-plan.md)
- [Plugin 端到端流程说明](./03-plugin-end-to-end-flow.md)
- [Plugin Runtime 架构](./design/03-runtime-architecture.md)
- [MCP / OpenAPI 接入策略](./design/04-mcp-openapi-strategy.md)
- [开源项目参考与复用策略](./design/06-open-source-reference-and-reuse.md)
- [0-1 开发计划与粗估](./design/07-development-plan-and-estimation.md)
- [POC 验收说明与后续 Roadmap](./04-poc-acceptance-and-roadmap.md)
- [POC 代码分层与部署映射](./05-code-structure-and-deployment-mapping.md)
