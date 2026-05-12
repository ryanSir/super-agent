# Plugin 端到端流程说明

本文补充 `plugin-runtime-architecture.svg` 的流程视角，说明插件从开发、发布、安装、启用，到业务 Agent 发现并调用插件能力的完整链路。

## 流程图

- 可编辑源文件：[plugin-end-to-end-flow-swimlane.drawio](./plugin-end-to-end-flow-swimlane.drawio)
- 导出图：[plugin-end-to-end-flow-swimlane.svg](./plugin-end-to-end-flow-swimlane.svg)

## 泳道和部署边界

这张图里的泳道表示 **职责边界**，不表示每个泳道都必须独立部署成一个服务。

建议第一版按以下部署边界理解：

| 泳道 | 是否独立服务 | 说明 |
| --- | --- | --- |
| 开发侧：Plugin Developer / SDK / CLI | 否 | 本地开发工具和命令行，不是线上服务 |
| 平台管理面：Plugin Registry / Plugin Manager | 你们需要建设；可合并，也可拆分 | 第一版可以作为 Plugin 管理平台的一部分；后续 Registry 可独立为制品仓库或 marketplace |
| 业务 Agent 系统：现有业务应用 / Agent Runtime | 各业务团队已有或自行建设 | 这是插件能力的使用方，后续通过 Plugin 核心服务对接插件平台 |
| Plugin 核心服务 | 你们需要建设 | 负责插件能力治理和调用，提供 Capability Resolver、Policy Engine、Credential Broker、Tool Invocation Gateway |
| 插件运行时服务：Plugin Runtime Host | 你们需要建设，建议独立 | 用于承载插件执行、MCP adapter、本地 daemon、sidecar 或 remote runtime，避免插件影响业务 Agent 主进程 |
| 外部依赖：SaaS / MCP Server / API / 数据源 / Observability 后端 | 复用现有系统 | MCP/API/数据源通常已有；观测监控可以接入现有 Langfuse |

也就是说，**业务 Agent 系统** 是图中绿色泳道；它不是 Plugin 系统本身，而是 Plugin 能力的使用方。业务 Agent 通过 **Plugin 核心服务** 发现和调用插件能力，不直接依赖插件包内部实现。

你们侧第一版主要需要部署：

- Plugin 核心服务
- Plugin 管理平台
- Plugin Runtime Host

各业务团队侧主要需要完成：

- 在业务 Agent 中接入 Plugin 核心服务的能力发现和调用接口
- 按 workspace/agent 维度申请或绑定可用插件能力

现有基础设施侧可以复用：

- 已有 MCP Server、企业 API、SaaS、数据库或数据源
- 已有 Langfuse 观测能力，用于承接 trace、tool call、error、latency、audit 等事件

## 核心流程

1. 插件开发者编写 `plugin.yaml` 和子配置文件。
2. 使用 CLI 做 `validate`、`package`、`publish`。
3. Registry 保存插件包、metadata 和 manifest snapshot。
4. Plugin Manager 从 Registry 安装插件。
5. 管理员按 workspace/agent 启用插件。
6. Plugin Manager 构建 Capability Index。
7. 业务 Agent 收到任务后，通过 Capability Resolver 获取可用能力。
8. Agent 根据任务选择 tool、skill、data source、OpenAPI 或 MCP 能力。
9. 调用前经过 Policy Engine 和 Credential Broker。
10. Tool Invocation Gateway 统一分发调用。
11. Plugin Runtime Host 执行对应 runtime。
12. 外部 API、MCP server 或数据源返回结构化结果。
13. Observability / Audit 记录调用和运行事件。
14. Agent 基于结构化结果和 skill context 生成最终回答。

## 与当前 POC 的映射

| 流程节点 | 当前 POC 实现 |
| --- | --- |
| 编写插件 | `plugin-poc/examples/slack-demo/plugin.yaml` |
| 校验插件 | `plugin_poc.developer_tooling.validator` / `plugin validate` |
| 打包插件 | `plugin_poc.developer_tooling.packager` / `plugin package` |
| 发布插件 | `plugin_poc.developer_tooling.publisher` / `plugin publish` |
| Registry | 本地文件 Registry，`index.json` + `package.zip` |
| 安装插件 | `plugin_poc.management.manager.install_plugin` / `plugin install` |
| 启用插件 | `plugin_poc.management.manager.enable_plugin` / `plugin enable` |
| Capability Index | `capability_index.json` / `list-capabilities` |
| Skill context | `plugin_poc.runtimes.skill_runtime` / `render-skill-context` |
| Policy Engine | `plugin_poc.core.policy` |
| Credential Broker | `plugin_poc.core.credentials` |
| Tool Invocation Gateway | `plugin_poc.core.gateway.invoke_capability` / `plugin invoke` |
| OpenAPI Runtime | `plugin_poc.runtimes.openapi_runtime` |
| MCP Runtime | `plugin_poc.runtimes.mcp_runtime` |
| Data Source Runtime | `plugin_poc.runtimes.data_source_runtime` |
| Runtime Host | `plugin_poc.runtime_host` / `start-runtime` |
| Audit Log | `audit_log.jsonl` / `list-audit` |
| Runtime Events | `runtime_events.jsonl` / `list-events` |
| E2E 验收 | `run-e2e` |

## 评审时的重点

这张图可以用来说明两个结论：

1. Plugin 不是单个工具协议，而是一个可分发的 Agent 能力包，覆盖工具、技能、数据源、OpenAPI、MCP、凭据、权限和观测。
2. 业务 Agent 不直接依赖插件内部实现，而是通过 Capability Index、Policy、Credential 和 Gateway 间接调用插件能力，从而降低对现有 Agent Runtime 的侵入。
