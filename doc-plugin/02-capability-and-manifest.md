# 02. 能力模型与 Manifest 草案

## 目标

本文件定义 Plugin 可以暴露哪些能力、Agent 如何发现和调用这些能力，以及 manifest 应该如何声明插件元数据。

## 能力模型

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

## 能力注册与 Agent 调用

Plugin 被安装和启用后，需要向平台注册一组可被 Agent 发现、选择和调用的能力。Agent Runtime 不直接理解插件内部实现，而是通过 Capability 元数据、Capability Resolver 和 Tool Invocation Gateway 使用插件能力。

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

## Manifest 设计

Plugin 必须包含 manifest，用于声明插件身份、能力、权限、认证、运行时和资源要求。manifest 可以采用 YAML 或 JSON，两者都需要配套 schema 校验。

常见组织方式：

| 方式 | 说明 | 适用场景 |
| --- | --- | --- |
| `plugin.yaml` | 单文件 YAML manifest | 开发者友好，适合作为默认推荐 |
| `plugin.json` | 单文件 JSON manifest | 机器处理友好，适合自动生成或严格校验 |
| `plugin.yaml` + `plugin.schema.json` | YAML 编写，JSON Schema 校验 | 推荐方案，兼顾可读性和校验能力 |
| 分层 manifest | 主 manifest 引用 tools、credentials、openapi 等子文件 | 插件能力复杂时使用 |

本规划建议第一版采用 `plugin.yaml` 作为开发者编写入口，并提供 `plugin.schema.json` 做校验；复杂插件可以通过 `path` 引用子配置文件。

## Manifest 示例

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
      transport: streamable_http
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

## Manifest 必须解决的问题

- 插件身份：`id/name/version/author`
- 插件能力：`skills/tools/mcp/openapi/data_sources/app`
- 运行方式：`local/remote/serverless/container`
- 权限声明：读、写、敏感操作
- 认证方式：OAuth、API Key、Bearer Token、企业 SSO
- 资源要求：内存、超时、并发、网络访问
- 安全策略：是否需要用户确认、是否允许外发数据
- 观测策略：日志、指标、trace、审计
