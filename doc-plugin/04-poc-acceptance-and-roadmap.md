# Plugin POC 验收说明与后续 Roadmap

## 1. 文档目的

本文用于说明当前 Plugin POC 的完成范围、验证方式、端到端流程映射、部署边界、已知限制和后续生产化 Roadmap。

配套流程图：

- [端到端流程说明](./03-plugin-end-to-end-flow.md)
- [端到端流程泳道图 SVG](./plugin-end-to-end-flow-swimlane.svg)
- [端到端流程泳道图 draw.io 源文件](./plugin-end-to-end-flow-swimlane.drawio)
- [代码分层与部署映射](./05-code-structure-and-deployment-mapping.md)

## 2. 当前 POC 结论

当前 POC 已经验证 Plugin 作为 Agent 能力包的基础闭环：

```text
开发插件
  -> 校验
  -> 打包
  -> 发布到 Registry
  -> 安装
  -> 启用并绑定 workspace/agent
  -> 生成 Capability Index
  -> 业务 Agent 发现能力
  -> Policy / Credential 检查
  -> Gateway 统一调用
  -> Runtime 执行
  -> 返回结构化结果
  -> Audit / Events 记录
```

这说明第一版 Plugin 平台可以按以下职责拆分推进：

- Plugin 管理平台：插件注册、安装、启用、配置、版本和凭据管理。
- Plugin 核心服务：能力发现、权限、凭据、统一调用网关。
- Plugin Runtime Host：插件运行隔离、MCP/OpenAPI/Data Source/Skill runtime。
- 业务 Agent 系统：各业务团队已有系统，通过 Plugin 核心服务接入插件能力。

当前 POC 的核心价值是先把整体模块边界和端到端链路定下来，而不是一次性完成生产级实现。

当前骨架包括：

```text
Manifest / Package / Registry
Plugin Manager
Capability Index
Policy
Credential
Invocation Gateway
OpenAPI Runtime
MCP Runtime
Skill Runtime
Data Source Runtime
Runtime Host
Audit / Events
E2E
```

后续生产化不建议简单把当前 POC 整体替换为某个开源框架，而是基于这些模块边界，逐个模块评估自研、复用、fork 或接入公司已有系统。

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

## 3. 阶段分层理解

当前 11 个阶段可以按平台能力成熟度分成四层，而不是理解成 11 个彼此独立的功能点。

| 阶段范围 | 主题 | 定位 |
| --- | --- | --- |
| Phase 1-4 | 插件接入与调用主链路 | Plugin 最小闭环 |
| Phase 5-8 | 能力类型与 Runtime 扩展 | 在主链路上扩展不同插件能力 |
| Phase 9-10 | Runtime 管理与观测治理 | 运行态管理、健康检查、事件和超时 |
| Phase 11 | E2E 验收 | 端到端回归验证入口 |

### Phase 1-4：插件接入与调用主链路

Phase 1-4 已经形成一个最小完整流程：

```text
插件编写
  -> 校验 / 打包 / 发布
  -> 安装 / 启用
  -> 能力发现
  -> 权限与凭据检查
  -> Agent 调用 tool
  -> 返回统一 Invocation Result
  -> Audit 记录
```

这几阶段回答的是 Plugin 平台最基础的问题：

- 插件怎么描述、校验、打包和发布。
- 插件怎么安装到平台。
- 插件怎么启用给指定 workspace / agent。
- Agent 怎么发现插件暴露的能力。
- 调用前怎么做 credential 和 policy 检查。
- 调用结果怎么用统一结构返回。
- 调用过程怎么审计。

因此，Phase 1-4 可以理解为 **Plugin 接入与调用闭环**。

### Phase 5-8：能力类型与 Runtime 扩展

Phase 5-8 不是新的主链路，而是在 Phase 1-4 的 `invoke` 框架上扩展更多 capability 类型：

```text
OpenAPI Runtime
MCP Runtime
Skill Runtime
Data Source Runtime
```

这些阶段主要回答：

- API 类能力怎么执行。
- MCP 工具怎么接入。
- Skill 怎么暴露给 Agent 上下文。
- Data Source 怎么作为查询或检索类能力返回结果。
- 不同 capability 类型如何统一走 Capability Index、Policy、Credential 和 Invocation Gateway。
- 不同 runtime 如何返回统一结构。

因此，Phase 5-8 可以理解为 **插件能力类型扩展与 Runtime 执行机制**。

### Phase 9-10：Runtime 管理与观测治理

Phase 9-10 把 POC 从“能调用”推进到“可管理、可观测”：

```text
Runtime Host
  -> stdio adapter metadata
  -> runtime health
  -> runtime event
  -> timeout
```

这些阶段主要回答：

- 插件 runtime 如何启动、停止和查询健康状态。
- stdio MCP adapter 的配置形态如何表达。
- 每次 runtime 调用如何记录事件。
- 调用超时如何被统一表达。
- Audit 和 Runtime Event 如何分工。

### Phase 11：E2E 验收

Phase 11 不新增能力类型，而是把 Phase 1-10 串起来做端到端验收。日常开发时可以优先跑 Phase 11；如果失败，再回到对应阶段文档定位具体模块。

一句话总结：

**Phase 1-4 是 Plugin 平台的骨架主链路；Phase 5-8 是在主链路上接入不同能力类型；Phase 9-10 是运行态治理；Phase 11 是端到端验收。**

## 4. 已实现能力

| 阶段 | 能力 | 当前实现 |
| --- | --- | --- |
| Phase 1 | 插件规范、校验、打包、发布 | `developer_tooling/validator.py`、`developer_tooling/packager.py`、`developer_tooling/publisher.py` |
| Phase 2 | 安装、启用、Capability Index | `management/manager.py`、`management/capability.py` |
| Phase 3 | 统一调用网关 | `core/gateway.py` |
| Phase 4 | 凭据、权限、审计 | `core/credentials.py`、`core/policy.py`、`core/audit.py` |
| Phase 5 | OpenAPI Runtime | `runtimes/openapi_runtime.py`，当前为 mock runtime |
| Phase 6 | Streamable HTTP MCP Runtime | `runtimes/mcp_runtime.py`，已用真实 stage MCP endpoint 验证 |
| Phase 7 | Skill Runtime | `runtimes/skill_runtime.py`，支持 `SKILL.md` 加载和 context 渲染 |
| Phase 8 | Data Source Runtime | `runtimes/data_source_runtime.py`，支持本地 JSON 数据源 |
| Phase 9 | Runtime Host / stdio adapter PoC | `runtime_host/host.py`，支持 lifecycle state 和 stdio adapter metadata |
| Phase 10 | Runtime Events / Timeout | `core/observability.py`，支持事件日志和超时模拟 |
| Phase 11 | E2E 验收 | `acceptance/e2e.py`，支持 `run-e2e` |

## 5. 一键验收

在项目根目录执行：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli run-e2e \
  --plugin-dir plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-e2e-registry \
  --state /tmp/plugin-poc-e2e-state
```

验收通过时返回：

```json
{
  "status": "ok"
}
```

该命令会验证：

- 发布插件到 Registry
- 从 Registry 安装插件
- 启用插件并绑定 `workspace + agent`
- 配置凭据
- 启动 Runtime Host 状态
- 调用 tool capability
- 调用 data source capability
- 渲染 skill context
- 检查 runtime health

## 6. 测试命令

```bash
ruff check plugin-poc
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=plugin-poc python -m pytest -p no:capture plugin-poc/tests -q
```

当前验证结果：

```text
45 passed, 1 warning
```

warning 来自仓库 pytest 配置中的 `asyncio_mode`，不影响 Plugin POC 测试结果。

## 7. 关键命令索引

### 插件开发和发布

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate plugin-poc/examples/slack-demo
PYTHONPATH=plugin-poc python -m plugin_poc.cli package plugin-poc/examples/slack-demo --output /tmp/plugin-poc-dist
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo --registry /tmp/plugin-poc-registry --force
```

### 安装和启用

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

### 能力发现

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-capabilities \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

### 凭据配置

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli configure-credential company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --values '{"client_id":"demo-client","client_secret":"demo-secret"}'
```

### 调用能力

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --confirm-sensitive \
  --input '{"channel_id":"C001","text":"hello"}'
```

### Skill context

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli render-skill-context \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

### Runtime Host

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli start-runtime company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli runtime-health \
  --state /tmp/plugin-poc-state \
  --plugin-id company.slack-demo \
  --version 1.0.0
```

### 审计和事件

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-audit --state /tmp/plugin-poc-state
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-events --state /tmp/plugin-poc-state
```

## 8. 与流程图的映射

| 流程图节点 | POC 命令 / 模块 |
| --- | --- |
| 编写插件 | `examples/slack-demo/plugin.yaml` |
| 校验 / 打包 | `validate`、`package` |
| 发布插件 | `publish` |
| Registry 存储 | `/tmp/plugin-poc-registry` |
| 安装插件 | `install`，写入 `/tmp/plugin-poc-state/installed` |
| 启用 / 绑定 | `enable`，写入 `enabled_plugins.json` 和 `capability_index.json` |
| 业务 Agent 发现能力 | `list-capabilities`、`list-skills` |
| Skill 上下文装配 | `render-skill-context` |
| 权限检查 | `core/policy.py` |
| 凭据校验 | `core/credentials.py` |
| 统一调用网关 | `core/gateway.py` / `invoke` |
| Runtime 分发 | `runtime_host/host.py` |
| OpenAPI / MCP / Data Source / Skill | `runtimes/openapi_runtime.py`、`runtimes/mcp_runtime.py`、`runtimes/data_source_runtime.py`、`runtimes/skill_runtime.py` |
| Audit / Events | `audit_log.jsonl`、`runtime_events.jsonl` |

## 9. 部署边界理解

POC 中的 `--state` 目录模拟平台状态存储，`--registry` 目录模拟内部 Registry。

生产化后建议理解为：

| 边界 | 责任方 | 说明 |
| --- | --- | --- |
| 业务 Agent 系统 | 各业务团队 | 已有或自行建设，通过 Plugin 核心服务对接插件能力 |
| Plugin 核心服务 | Plugin 平台团队 | 能力发现、权限、凭据、统一调用 |
| Plugin 管理平台 | Plugin 平台团队 | Registry、Manager、安装、启用、配置、版本、凭据管理 |
| Plugin Runtime Host | Plugin 平台团队 | 插件执行、MCP adapter、OpenAPI/Data Source/Skill runtime、运行隔离 |
| 外部系统 | 现有系统 | MCP Server、企业 API、SaaS、数据库、知识库 |
| Observability | 复用现有能力 | 可接入 Langfuse，承接 trace、tool call、error、latency、audit |

## 10. 当前 POC 边界

当前 POC 已能证明主链路可行，但不是生产版：

- Registry 是本地文件目录，不是正式制品仓库或 marketplace。
- Plugin Manager 状态是 JSON 文件，不是数据库。
- OpenAPI Runtime 是 mock runtime，还没有真实 HTTP 请求和凭据注入。
- stdio MCP adapter 只登记 metadata，没有真正启动子进程做代理。
- Credential 只做字段校验和脱敏展示，没有加密存储。
- Policy 是最小规则，没有接入公司 IAM / RBAC / ABAC。
- Runtime Host 是生命周期状态模型，没有进程、容器或 sidecar 隔离。
- Observability 写本地 JSONL，没有接入 Langfuse。
- Admin Console 未实现。
- 业务 Agent 对接目前用 CLI 模拟，没有提供 HTTP API / SDK。

## 11. 后续生产化 Roadmap

### M1：服务化改造

- 将 CLI 能力拆成 HTTP API。
- 建设 Plugin 核心服务。
- 建设 Plugin 管理平台后端。
- 使用数据库保存 plugin、version、install、enable、capability、credential、audit 状态。

### M2：Registry 和包治理

- 接入内部制品仓库或建设内部 Plugin Registry。
- 增加 plugin package 签名、checksum 校验、版本状态、审核状态。
- 增加 plugin schema 版本兼容策略。

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

## 12. 建议评审问题

评审时建议重点确认：

1. 业务 Agent 对接方式：HTTP API、SDK，还是网关协议。
2. Plugin 核心服务是否作为独立服务部署。
3. Plugin 管理平台和 Registry 是否复用内部制品仓库。
4. Runtime Host 第一版采用 daemon、sidecar 还是 remote runtime。
5. stdio MCP 是否第一版必须支持真实托管。
6. Credential 是否第一版必须支持 OAuth2 refresh。
7. Policy 是否接入现有权限系统。
8. Observability 是否直接接入 Langfuse。
9. Admin Console 第一版是否必须交付。
10. 第一批官方插件选哪些，用于 MVP 验收。
