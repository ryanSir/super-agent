# 01. 模块开发总计划

## 模块分层

生产化开发建议按以下模块推进：

| 层级 | 模块 | 第一阶段建议 | 说明 |
| --- | --- | --- | --- |
| 插件规范层 | Manifest / Schema / Package Layout | 必做 | 定义插件包结构、能力声明、版本、权限、凭据、展示元数据 |
| 管理层 | Registry / Plugin Manager | 必做 | 插件发布、安装、启用、禁用、版本状态和 workspace / agent 绑定 |
| 索引层 | Capability Index | 必做 | 为 Agent 提供按作用域过滤后的能力视图 |
| 调用层 | Plugin Core API / Invocation Gateway | 必做 | 能力发现、权限检查、凭据注入、统一调用、错误归一 |
| 能力层 | Skill / OpenAPI / Streamable HTTP MCP / Data Source | 分阶段 | 第一阶段优先 Skill + OpenAPI；MCP 只考虑 Streamable HTTP；Data Source 后续评估 |
| 治理层 | Policy / Credential / Audit | 后置 | 第一阶段只预留接口和默认放行策略，后续再接公司 IAM / 密钥系统 |
| 集成层 | 当前 `src_deepagent` 集成 | 后置 | Plugin 平台自身链路完成后，再用当前 Agent 做真实调用测试 |
| 管理后台 | Admin Console | 必做 | 第一阶段纳入管理平台骨架，覆盖列表、详情、安装、启用和能力索引查看 |
| 运行层 | Runtime Host | 待定 | 第一阶段不做；只在确实需要 stdio MCP / 本地代码托管时评估 |
| 扩展层 | Workflow / Trigger / App/UI / Agent Strategy | 待定 | 后续按业务场景单独评估 |

## 第一阶段开发顺序

当前已进入 OpenSpec change：`build-production-plugin-platform`。

第一阶段实现原则：

- 先跑通主体功能。
- Plugin 平台独立放在 `plugin-platform/`，不改 `src_deepagent`。
- 使用可替换的本地 dev store 验证发布、安装、启用和能力索引。
- 先暴露稳定 Backend API，当前 Agent 后续作为外部调用方接入。
- Policy、Credential、Audit 只做接口占位。
- MCP 只验证 Streamable HTTP，不做 stdio MCP adapter。

### M0：详细设计冻结

输出：

- 模块边界。
- 数据模型。
- API 设计。
- 后续当前 Agent 集成边界。
- 开源深度分析结论。
- 第一阶段治理能力降级策略。

完成标准：

- 每个第一阶段模块都有明确输入、输出、依赖和验收方式。
- 明确哪些功能复用 POC 思路，哪些重新设计。

### M1：插件规范和包结构

开发内容：

- 生产版 `plugin.yaml` schema。
- package layout。
- manifest version 和 capability version 策略。
- plugin id、version、publisher、category、display metadata。
- tools、skills、openapi、mcp、credentials、policy 的声明结构。

参考：

- Codex Plugins。
- Dify manifest。
- ccpkg / Open Plugins。
- 当前 `plugin-poc/schemas/plugin.schema.json`。

验收：

- 能校验真实示例插件。
- 能生成结构化错误。
- 能兼容后续 Registry 和 Capability Index。

### M2：Registry 和 Plugin Manager

开发内容：

- 插件包存储抽象。
- 插件版本元数据。
- install / uninstall / enable / disable。
- workspace / agent 绑定。
- 状态持久化。

参考：

- Codex marketplace 和 enable / disable 模型。
- 公司内部制品仓库。

验收：

- 一个插件可以被安装到平台。
- 一个插件可以被启用给指定 workspace / agent。
- 禁用后 Agent 不再发现其能力。

### M3：Capability Index、Plugin Core API 和 Admin Console 骨架

开发内容：

- Capability Index 生成和查询。
- Capability Discovery API。
- Skill Context API。
- Tool Invocation API。
- 统一错误结构和调用结果结构。
- Admin Console 基础页面。
- Policy / Credential / Audit 接口占位，第一阶段默认最小实现，不阻塞主链路。

验收：

- Backend API 能查询 workspace / agent 作用域能力。
- Admin Console 能查看 Registry、插件详情、安装状态和能力索引。
- 当前 Agent 集成不在本阶段验收范围内。

### M4：能力调用跑通

开发内容：

- OpenAPI / HTTP connector 真实调用。
- Streamable HTTP MCP 基础调用。
- 统一输入输出 schema。
- 统一错误结构。
- 调用超时和失败返回。

参考：

- OpenAPI tooling。
- 当前 `plugin-poc` 的 OpenAPI / MCP Runtime。
- MCP 官方 Streamable HTTP Transport 规范。

验收：

- 至少一个 OpenAPI / HTTP 插件能力可以通过 Plugin Runtime 边界调用。
- 如果第一阶段包含 MCP，则只验证 Streamable HTTP MCP。
- 调用失败时返回结构化错误，不中断 Agent 主流程。

### M5：Plugin 平台端到端测试

开发内容：

- 建立测试插件。
- 通过 CLI 完成 validate / package。
- 通过 Backend API 完成 publish / install / enable / capability discovery。
- 通过 Admin Console 完成同类操作。

验收：

- 不只跑 CLI，也要通过 Backend API 和管理平台验证。
- 能看到 capability discovery 和 invocation result。
- trace、audit、policy、credential 可以先用占位实现，后续再补完整治理。

### M5.5：当前 Agent 集成测试（后置）

开发内容：

- 将当前 Agent 作为 Plugin Platform 的外部消费者。
- 通过 Capability Discovery API 获取 workspace / agent 能力。
- 将 Skill Context 注入 Agent 上下文。
- 通过 Plugin Core API 调用 OpenAPI / Streamable HTTP MCP 能力。

验收：

- 不污染 `src_deepagent` 的核心模块边界。
- Agent 能发现、选择、调用插件能力。
- 集成测试作为独立 OpenSpec change 推进。

### M6：治理能力补齐

开发内容：

- Credential schema。
- Credential reference 和脱敏展示。
- Policy check 接口。
- audit log。
- 接入公司密钥系统、IAM / RBAC / ABAC。

验收：

- 没有配置凭据时调用失败。
- 没有权限时调用失败。
- 调用成功和失败都能记录审计。

## 后续候选

第二阶段不提前承诺，按第一阶段结果和业务需求评估：

- Data Source Plugin。
- Langfuse / 观测平台深度集成。
- Runtime Host。
- stdio MCP adapter。
- Workflow / Trigger / App/UI。
