# Plugin 能力规划草案

## 1. 背景与目标

公司 Agent 平台需要一种标准化扩展机制，用于把外部数据、企业系统、工具服务、领域流程和 UI 能力接入 Agent Runtime。

该机制暂称为 **Plugin**。内部更准确的抽象可以叫 **Capability Package，能力包**。

Plugin 的目标不是简单封装一个 API，而是提供一套完整能力：

- 可声明：通过 manifest 描述能力、权限、运行时、认证、资源。
- 可安装：支持平台安装、启用、禁用、升级、卸载。
- 可授权：支持租户、用户、workspace 级权限控制。
- 可运行：支持 MCP、OpenAPI、原生工具、数据源、workflow 等运行方式。
- 可观测：支持调用日志、错误、成本、审计、链路追踪。
- 可分发：支持内部 registry、外部 marketplace、版本管理。

开源项目参考：

- Dify 的 plugin daemon/runtime 设计值得重点参考，可借鉴其对插件生命周期、运行隔离和调试模式的处理方式。
- Open WebUI 展示了多扩展形态并存的设计，包括 MCP、OpenAPI、Tools 和 Pipelines，可参考其扩展分层与协议适配方式。
- n8n 的连接器生态值得参考，尤其是凭据配置 schema、连接测试、节点市场和 API 集成开发体验。
- Open Plugins/ccpkg 的包结构可作为参考，适合借鉴其将 skills、MCP、hooks、agents 等能力统一打包的方式。
- mcpo 的 MCP-to-OpenAPI adapter 思路值得参考，可用于降低 MCP 工具接入和平台统一治理的复杂度。

参考来源：

- [Dify Plugin Manifest][dify-plugin-manifest]
- [dify-plugin-daemon][dify-plugin-daemon]
- [Open WebUI Extensibility][open-webui-extensibility]
- [Open WebUI MCP][open-webui-mcp]
- [mcpo][mcpo]
- [Open Plugins][open-plugins]
- [ccpkg][ccpkg]
- [n8n Integrations][n8n-integrations]

[dify-plugin-manifest]: https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest
[dify-plugin-daemon]: https://github.com/langgenius/dify-plugin-daemon
[open-webui-extensibility]: https://docs.openwebui.com/features/extensibility/
[open-webui-mcp]: https://docs.openwebui.com/features/extensibility/mcp/
[mcpo]: https://github.com/open-webui/mcpo
[open-plugins]: https://open-plugins.com/
[ccpkg]: https://ccpkg.dev/
[n8n-integrations]: https://docs.n8n.io/integrations/

## 2. 核心定义

中文定义：

> Plugin 是一个声明式、可安装、可授权、可运行、可观测、可分发的 Agent 能力包，用于将外部系统、数据源、工具调用、技能流程或 UI 组件接入 Agent 平台。

英文定义：

> Plugin is a declarative, installable, permissioned, executable, observable and distributable capability package that extends the Agent Platform with external systems, data sources, tool invocations, skills, workflows and optional UI components.

## 3. 与 Skill / Tool / MCP / App 的关系

Plugin 是分发和治理单元，不是具体执行能力本身。

```text
Plugin / Capability Package
   ├── Skill：告诉 Agent 如何完成某类任务
   ├── Tool：Agent 可调用的结构化函数
   ├── MCP Server：一种工具协议接入方式
   ├── OpenAPI Connector：一种企业 API 接入方式
   ├── Data Source：文档、数据库、SaaS、知识库等数据接入
   ├── Workflow：可复用流程或自动化编排
   ├── App/UI：配置页、操作面板、结果展示
   ├── Auth/Credentials：认证和凭据声明
   └── Policy：权限、审计、人审、数据边界
```

| 概念 | 定位 |
| --- | --- |
| Plugin | 能力包、安装包、治理单元 |
| Skill | Agent 行为指导和领域工作流说明 |
| Tool | 可被模型调用的结构化能力 |
| MCP | Tool/Data 的协议之一 |
| OpenAPI | 企业 API 接入协议之一 |
| App | 用户可见的配置和交互界面 |
| Connector | 面向外部系统的数据/操作接入器 |

关键结论：**MCP 不是 Plugin 本身，MCP 是 Plugin 支持的一种运行时或工具协议。**

## 4. Plugin 能力模型

第一版建议支持以下能力类型：

| 能力类型 | 第一版是否支持 | 说明 |
| --- | --- | --- |
| Tool Plugin | 是 | 封装可调用工具，比如查 Jira、发消息、查订单 |
| API Connector Plugin | 是 | 基于 OpenAPI/REST/GraphQL 接入企业系统 |
| MCP Plugin | 是 | 接入 MCP server，优先支持 Streamable HTTP，stdio 通过 adapter |
| Skill Plugin | 是 | 封装领域任务流程和 Agent 使用说明 |
| Data Source Plugin | 是 | 接入知识库、数据库、文档、SaaS 数据 |
| Credential Plugin | 是 | 声明认证方式、配置表单、凭据测试 |
| Workflow Plugin | 二期 | 封装多步骤自动化流程 |
| Trigger Plugin | 二期 | 外部事件触发 Agent 或 Workflow |
| App/UI Plugin | 二期 | 插件配置页、操作面板、可视化结果 |
| Agent Strategy Plugin | 暂不纳入 | Dify 中存在类似类型，但当前阶段容易与 Skill Plugin 混淆，且会影响 Agent Runtime 核心机制 |
| Model Provider Plugin | 暂缓 | 除非平台近期要做模型供应商生态 |

## 5. 能力注册与 Agent 调用模型

Plugin 被安装和启用后，需要向平台注册一组可被 Agent 发现、选择和调用的能力。Agent Runtime 不直接理解插件内部实现，而是通过标准化的 Capability 元数据、Capability Resolver 和 Tool Invocation Gateway 使用插件能力。

端到端流程详见：[Plugin 端到端流程说明](./03-plugin-end-to-end-flow.md)。

![Plugin 端到端流程泳道图](./plugin-end-to-end-flow-swimlane.svg)

```text
Plugin
   │
   ├── 声明 capabilities
   │      ├── tools
   │      ├── skills
   │      ├── data_sources
   │      ├── workflows
   │      └── apps
   │
   ▼
Plugin Manager
   │  安装、启用、配置、绑定 workspace / agent
   ▼
Capability Index
   │  记录当前 Agent 可用能力
   ▼
Agent Runtime
   │
   ├── Capability Resolver：发现可用能力
   ├── Policy Engine：检查是否允许使用
   ├── Credential Broker：注入调用凭据
   └── Tool Invocation Gateway：统一发起调用
```

Plugin 暴露给 Agent 的能力可以分为几类：

| 能力 | Agent 如何使用 | 示例 |
| --- | --- | --- |
| Tool | 直接调用结构化方法或 API | `search_issues`、`send_message`、`query_customer` |
| Skill | 作为任务策略、流程指导和提示词约束 | 分析 Sprint 风险、生成周报、拆解需求任务 |
| Data Source | 检索或查询业务上下文 | 查询知识库、CRM 记录、工单历史 |
| Workflow | 执行一段固定多步骤流程 | 创建事故复盘报告、发起审批流程 |
| Trigger | 外部事件触发 Agent 或 workflow | 新工单创建、告警触发、文档更新 |
| App/UI | 面向用户的配置、授权和交互界面 | 插件配置页、结果面板、操作表单 |

Tool 和 Skill 需要明确区分：

- Tool 是 Agent 可以直接调用的结构化函数或 API，强调“能执行什么动作”。
- Skill 是 Agent 完成某类任务的方法、流程和约束，强调“如何组织工具和上下文完成任务”。

以 Jira Plugin 为例：

```text
Jira Plugin
   ├── Tools
   │   ├── search_issues()
   │   ├── get_issue()
   │   ├── create_issue()
   │   └── update_issue()
   │
   ├── Skills
   │   ├── summarize_sprint_risk
   │   └── convert_prd_to_jira_tasks
   │
   └── Data Sources
       └── jira_project_issues
```

Agent 使用流程示例：

```text
用户：帮我分析这个 Sprint 有没有延期风险
  ↓
Agent 判断需要 Jira 相关能力
  ↓
Capability Resolver 发现 Jira Plugin 已启用
  ↓
读取 summarize_sprint_risk skill
  ↓
调用 search_issues / get_issue 等 tools
  ↓
结合 Jira 数据生成风险分析
```

这意味着 Plugin 系统需要维护一份可查询的能力索引，至少包含：

- 哪些 plugin 已安装、已启用。
- 每个 plugin 暴露哪些 tools、skills、data sources、workflows。
- 每个能力属于哪个 workspace、agent、用户或租户。
- 每个能力需要哪些权限和凭据。
- 每个能力的输入输出 schema、描述、示例和调用约束。
- 每个能力的版本、来源、启用状态和审计策略。

## 6. Manifest 设计

Plugin 必须包含 manifest，建议使用 YAML 或 JSON。YAML 对开发者更友好，JSON Schema 对校验更友好。可以采用 `plugin.yaml` + `plugin.schema.json`。

示例：

```yaml
schema_version: 0.1.0
id: company.slack
name: Slack
version: 1.0.0
description: Slack connector for Agent Platform
author: company
type: capability_package

capabilities:
  skills:
    - path: skills/summarize-channel/SKILL.md
  tools:
    - path: tools/slack-tools.yaml
  mcp:
    - name: slack-mcp
      transport: http
      url: https://plugin-runtime.company.com/slack/mcp
  openapi:
    - name: slack-api
      spec: openapi/slack.yaml
  data_sources:
    - path: data_sources/slack-messages.yaml

auth:
  type: oauth2
  scopes:
    - channels:read
    - chat:write
  credential_schema: credentials/oauth.yaml

permissions:
  read:
    - slack.channels
    - slack.messages
  write:
    - slack.messages
  sensitive_actions:
    - send_message
    - invite_user

runtime:
  mode: remote
  entrypoint: runtime/server
  resource:
    memory_mb: 512
    timeout_seconds: 30

policy:
  requires_user_consent: true
  audit_level: full
  data_retention: platform_default

observability:
  traces: true
  metrics: true
  logs: true
```

manifest 必须解决的问题：

- 插件身份：`id/name/version/author`
- 插件能力：`skills/tools/mcp/openapi/data_sources/app`
- 运行方式：`local/remote/serverless/container`
- 权限声明：读、写、敏感操作
- 认证方式：OAuth、API Key、Bearer Token、企业 SSO
- 资源要求：内存、超时、并发、网络访问
- 安全策略：是否需要用户确认、是否允许外发数据
- 观测策略：日志、指标、trace、审计

## 7. 运行时架构

`Plugin Runtime Host` 是架构抽象，表示插件能力的实际执行宿主。技术选型阶段需要全面比较候选运行形态，包括 in-process、local daemon、sidecar、remote service、container runtime、serverless runtime 和 hybrid runtime，再决定第一版主路径。

![Plugin Runtime Architecture](./plugin-runtime-architecture.svg)

这里需要区分管理面和调用面：

- 管理面：`Plugin Registry -> Plugin Manager -> Plugin Runtime Host`，负责插件发布、安装、启用、配置、升级、停止和卸载。
- 调用面：`Agent Runtime -> Capability Resolver -> Tool Invocation Gateway -> Plugin Runtime Host`，负责在用户请求中发现并调用已启用的插件能力。

`Plugin Manager` 不在每次 Agent 工具调用的主链路上。它负责把插件安装状态、启用状态、能力定义和绑定关系写入能力索引；Agent 调用时由 `Capability Resolver` 使用这些信息找到可用能力。

核心组件：

| 组件 | 职责 |
| --- | --- |
| Plugin Registry | 插件存储、搜索、版本、签名、审核状态 |
| Plugin Manager | 安装、启用、禁用、升级、卸载 |
| Plugin Runtime Host | 隔离运行插件，管理进程、容器、serverless、sidecar 或远程服务 |
| Capability Resolver | 根据 Agent 上下文找到可用能力 |
| Policy Engine | 权限、租户、敏感操作、人审 |
| Credential Broker | 凭据加密、注入、刷新、隔离 |
| Tool Gateway | 统一调用 MCP/OpenAPI/native tools |
| Observability | 日志、trace、调用记录、错误、成本 |

运行形态初步建议：

| 运行形态 | 第一版建议 | 说明 |
| --- | --- | --- |
| In-process | 不建议 | 隔离差，插件异常或依赖冲突可能影响 Agent 主进程 |
| Local daemon | 推荐 PoC | 适合托管 MCP stdio、本地插件和调试 |
| Sidecar | 作为增强方向评估 | 适合按 tenant/workspace/agent 做强隔离 |
| Remote service | 推荐支持 | 适合企业 API connector 和已有服务接入 |
| Container runtime | 二期评估 | 隔离强，但编排、镜像和安全扫描复杂 |
| Serverless runtime | 二期/三期评估 | 弹性好，但冷启动、状态管理和调试复杂 |
| Hybrid | 长期目标 | 不同插件按能力类型、安全等级和部署要求选择不同 runtime |

能力发现和能力执行需要解耦：`Capability Resolver` 负责基于能力索引发现可用能力；`Plugin Runtime Host` 负责根据 runtime 配置找到或拉起插件执行实例。

## 8. 调用链路

```text
User Request
   │
   ▼
Agent Planner
   │
   ▼
Capability Resolver
   │  找到可用 Plugin / Skill / Tool
   ▼
Policy Engine
   │  检查租户、用户、权限、敏感操作
   ▼
Credential Broker
   │  注入必要凭据，不暴露给模型
   ▼
Tool Invocation Gateway
   │  MCP / OpenAPI / Native Tool / Data Source
   ▼
Plugin Runtime Host
   │  执行插件能力
   ▼
Result Normalizer
   │  统一输出、错误码、引用来源
   ▼
Agent Response / UI Render
```

关键原则：**模型只看到必要的 tool schema 和结果，不直接接触密钥、内部网络细节和未授权数据。**

## 9. 安全与权限模型

第一版必须内置安全模型，不能后补。

权限分层：

```text
Tenant
   └── Workspace
          └── User / Agent
                 └── Plugin
                        └── Capability
                               └── Operation
```

权限类型：

| 类型 | 示例 |
| --- | --- |
| 数据读取 | 读取 Slack channel、读取 CRM 客户 |
| 数据写入 | 发送消息、创建工单、更新客户状态 |
| 敏感操作 | 删除数据、邀请用户、发外部邮件 |
| 网络访问 | 访问公网、访问内网服务 |
| 文件访问 | 读取上传文件、写入临时文件 |
| 用户代理 | 代表某用户执行 OAuth 操作 |
| 系统代理 | 使用平台级 service account |

安全要求：

- 凭据加密存储。
- 凭据只在 runtime 注入，不进入模型上下文。
- 插件声明权限，管理员授权。
- 敏感操作支持 human confirmation。
- 所有调用写审计日志。
- 插件运行环境隔离。
- 插件输出需要做结构化校验。
- 外部插件需要签名、审核和版本锁定。

## 10. Credential 设计

建议强参考 n8n。Credential 不应只是密钥字段，而是一套声明。

示例：

```yaml
id: slack_oauth
type: oauth2
fields:
  - name: client_id
    type: string
    required: true
  - name: client_secret
    type: secret
    required: true
authorization:
  auth_url: https://slack.com/oauth/v2/authorize
  token_url: https://slack.com/api/oauth.v2.access
  scopes:
    - channels:read
    - chat:write
test:
  method: GET
  url: https://slack.com/api/auth.test
```

平台能力：

- 凭据表单自动生成。
- OAuth 自动授权和刷新。
- 凭据 test connection。
- 凭据按租户/workspace/user 隔离。
- 调用时由 Credential Broker 注入。
- 支持 credential-only connector，即只有凭据和 OpenAPI spec，也可以生成工具。

## 11. MCP / OpenAPI 双协议策略

建议明确：

> 平台内部统一抽象为 Tool Invocation，外部接入同时支持 MCP 和 OpenAPI。

| 场景 | 推荐协议 |
| --- | --- |
| 企业系统 API | OpenAPI 优先 |
| 已有 MCP server | MCP 接入 |
| stdio MCP | 通过 mcpo-like adapter 转 Streamable HTTP 或 OpenAPI |
| 浏览器多租户平台 | 避免直接管理 stdio |
| 需要审计、配额、网关 | OpenAPI 更成熟 |
| 需要生态兼容 | MCP 更方便 |
| 老版 HTTP+SSE MCP | 作为兼容项支持，不作为新插件优先协议 |

架构：

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

## 12. Plugin 生命周期

```text
Develop
   │
   ▼
Validate
   │
   ▼
Package
   │
   ▼
Publish
   │
   ▼
Review
   │
   ▼
Install
   │
   ▼
Configure Credentials
   │
   ▼
Enable for Workspace / Agent
   │
   ▼
Invoke
   │
   ▼
Observe
   │
   ▼
Upgrade / Disable / Uninstall
```

| 阶段 | 平台能力 |
| --- | --- |
| Develop | SDK、CLI、模板、local debug |
| Validate | manifest schema、权限检查、安全扫描 |
| Package | 打包、签名、依赖锁定 |
| Publish | 上传 registry、版本管理 |
| Review | 人工/自动审核、隐私政策、权限说明 |
| Install | 租户安装、版本锁定 |
| Configure | 凭据配置、连接测试 |
| Enable | 绑定 workspace、agent、用户 |
| Invoke | 统一调用、权限检查、运行时执行 |
| Observe | 日志、trace、审计、错误 |
| Upgrade | 兼容性检查、灰度、回滚 |

## 13. 开发者体验

MVP 应提供：

```text
plugin init
plugin validate
plugin run
plugin debug
plugin package
plugin publish
```

推荐目录结构：

```text
my-plugin/
├── plugin.yaml
├── README.md
├── privacy.md
├── skills/
│   └── summarize-channel/
│       └── SKILL.md
├── tools/
│   └── tools.yaml
├── openapi/
│   └── service.yaml
├── mcp/
│   └── server.json
├── credentials/
│   └── oauth.yaml
├── data_sources/
│   └── source.yaml
├── runtime/
│   └── main.py
└── tests/
    └── plugin.test.yaml
```

开发者不应该一开始就必须写复杂代码。应该支持三种开发模式：

| 模式 | 面向用户 | 复杂度 |
| --- | --- | --- |
| Manifest-only | 配置型 connector | 低 |
| OpenAPI-based | API 集成开发者 | 中 |
| Runtime-coded | 高级插件开发者 | 高 |

## 14. MVP 范围

第一版建议聚焦：

1. Plugin manifest schema
2. Plugin registry 基础能力
3. Plugin install/enable/disable
4. OpenAPI connector plugin
5. Streamable HTTP MCP plugin
6. mcpo-like adapter 方案验证
7. Skill plugin
8. Credential schema + encrypted storage
9. Policy check + audit log
10. Tool invocation gateway
11. Local dev CLI
12. 2-3 个官方示例插件

第一版官方示例建议：

- 企业知识库 Data Source Plugin
- Jira/飞书/Slack API Connector Plugin
- MCP filesystem 或 GitHub MCP Plugin
- 周报生成 Skill Plugin

## 15. 二期路线图

二期可以做：

- Plugin marketplace
- 插件签名和安全扫描
- App/UI Plugin
- Workflow Plugin
- Trigger Plugin
- Serverless runtime
- 插件调用成本统计
- 插件权限审批流
- 多版本灰度和回滚
- 插件评分、文档、示例库

三期再考虑：

- Model Provider Plugin
- 插件组合编排
- 插件商业化结算
- 外部开发者生态

## 16. 关键设计原则

1. Plugin 是能力包，不是单个工具。
2. Manifest 是插件契约，Runtime 是执行细节。
3. MCP 和 OpenAPI 并存，平台内部统一 Tool Invocation。
4. 凭据不进入模型上下文，只由 Credential Broker 注入。
5. 插件必须先声明权限，再被授权运行。
6. Plugin Runtime 与 Agent Core 解耦。
7. 所有调用必须可审计、可追踪、可回放。
8. 第一版优先企业可控接入，不追求开放市场复杂生态。
9. 官方插件先跑通标准，再开放第三方开发。
10. 插件系统从第一天就按多租户、安全、版本治理设计。

## 17. 本周建议产出

本周建议完成 5 个成果：

1. Plugin 概念定义文档
2. Plugin 能力模型与 manifest 草案
3. Plugin Runtime 架构图
4. MCP/OpenAPI 接入策略
5. MVP 范围和路线图

关键决策建议：

> 第一版采用 “Dify-style Plugin Runtime + n8n-style Credential Model + OpenAPI/MCP Dual Protocol + Open Plugins-style Package Layout” 的组合路线。

这条路线比较稳：不会从零发明所有东西，也不会被某一个开源框架的边界锁死。
