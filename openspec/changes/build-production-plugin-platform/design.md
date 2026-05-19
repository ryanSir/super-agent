## Context

`doc-plugin` 已经形成 Plugin 平台总体报告，`plugin-poc` 验证了 manifest、能力索引、OpenAPI/MCP/Skill 等方向的可行性。但 POC 不是生产功能：它缺少独立部署边界、开发者交付链路、Registry/Manager、管理平台、版本模型和后续治理接口。

当前仓库本体是 Agent 项目。Plugin 平台在开发期可以放在 `plugin-platform/` 下方便联调，但必须保持独立模块边界，后续可以迁移到独立仓库或独立服务。当前 Agent 集成测试放到后续阶段，不作为一期实现目标。

## Goals / Non-Goals

**Goals:**

- 建立独立 Plugin 平台工作区，按未来真实部署单元拆分 backend、admin frontend、CLI/SDK、examples 和 tests。
- 支持插件开发者完成 `create -> validate -> package -> publish`。
- 支持平台管理员完成 `list -> inspect -> install -> enable/disable -> capability index`。
- 支持业务调用方通过稳定 API 发现能力，并为 OpenAPI、Streamable HTTP MCP、Skill Context 保留调用入口。
- 管理平台前端纳入一期设计，先实现插件列表、详情、安装、启用和配置查看的基础工作台。
- 对每个核心模块明确开源参考、可复用边界和自研边界。

**Non-Goals:**

- 不接入或改造 `src_deepagent` 当前 Agent Runtime。
- 不实现 stdio MCP adapter、本地 Runtime Host 或隔离执行环境。
- 不开放任意脚本 hook、长驻 monitor、Workflow Plugin、Trigger Plugin、Agent Strategy Plugin。
- 不在一期完成完整 IAM、Policy、Credential Broker、审计留存、Langfuse tracing，但接口和状态字段需要预留。

## Decisions

### 1. 独立工作区，而不是写入现有 Agent 代码

在 `plugin-platform/` 下建立生产平台工作区：

- `backend/`: FastAPI 服务、领域模型、Registry、Manager、Capability Index、runtime adapter。
- `admin-console/`: React + Vite 管理平台。
- `cli/`: 插件开发者 CLI，负责 validate/package/publish。
- `sdk/`: 后续给 Agent 或其他调用方使用的客户端契约。
- `examples/`: 示例插件。
- `tests/`: 平台级测试。

原因：Plugin 是平台能力，不是当前 Agent 的内部模块。这样可以避免污染 `src_deepagent`，也能贴近后续多部署单元的真实结构。

备选方案：直接在 `src_deepagent/plugins` 内实现。该方案方便短期集成，但会把 Plugin 平台和 Agent Runtime 绑定，不符合生产化边界，已放弃。

### 2. 一期以远程能力为主，暂不强调 Runtime Host

一期支持三类能力：

- OpenAPI / HTTP tool：适合已有 REST API 和内部服务。
- Streamable HTTP MCP：适合标准 MCP server，按 MCP 官方 Streamable HTTP transport 接入。
- Skill Context：适合向 Agent 提供上下文、使用说明、任务边界和提示词片段。

stdio MCP、本地 tool、隔离 runtime 等能力依赖 Runtime Host，后续再做。这样第一阶段可以先打通生产主链路，而不是过早进入沙箱、进程生命周期和本地执行安全问题。

### 3. Manifest 自研 schema，参考 Codex/Dify/n8n

`plugin.yaml` 作为主 manifest，子配置按能力类型拆分，例如 `skills/*.yaml`、`openapi/*.yaml`、`mcp/*.yaml`、`credentials/*.yaml`、`assets/*`。

参考边界：

- Codex Plugins：参考 plugin package、skills、MCP 配置、apps、assets、marketplace catalog 的组合包思路。
- Dify：参考 manifest 的插件基本信息、权限声明、runtime/meta、marketplace 展示字段。
- n8n：参考 credential schema、认证注入描述和 test request 的配置方式。

不直接照搬原因：公司平台需要 workspace/agent/IAM、内部制品仓库、内部密钥系统和统一管理后台，这些都需要自研适配。

### 4. Registry 与 Manager 分层

Registry 管“插件包和版本”，Manager 管“租户内安装和启用状态”。

- Registry 保存 package metadata、version、checksum、manifest、capability summary、publish status。
- Manager 保存 workspace 安装、agent 绑定、enabled/disabled、配置状态、capability index。

原因：同一插件版本可以被多个 workspace/agent 复用；安装启用是租户态，不应污染全局插件包元数据。

### 5. Admin Console 从一期开始，但先做管理闭环

管理平台一期不是营销页，也不是只展示说明文档，而是操作台：

- 插件市场/Registry 列表。
- 插件详情和版本。
- 安装、启用、禁用。
- workspace/agent 绑定关系。
- capability index 查看。
- 配置和凭据占位状态。

Policy、Credential、Audit 可以先展示状态和占位入口，后续补完整能力。

### 6. 数据存储采用接口优先，本地开发适配器先行

一期可以使用文件或 SQLite 作为 dev adapter，但代码必须按 repository/service 接口组织，避免后续迁移 Postgres、对象存储或内部制品仓库时改动业务层。

## Risks / Trade-offs

- [Risk] 一期不接入当前 Agent，短期看不到真实任务闭环 → Mitigation: 通过 CLI、Backend API、Admin Console 和 example plugin 先验收 Plugin 自身主链路，后续单独做 Agent integration change。
- [Risk] 只支持 Streamable HTTP MCP，无法接本地 stdio MCP → Mitigation: 明确 stdio adapter 后置；manifest 中保留 `transport` 枚举，拒绝 unsupported 类型并给出清晰错误。
- [Risk] 本地存储适配器被误当生产存储 → Mitigation: 文档和配置中标注 dev adapter，Repository 接口保持可替换。
- [Risk] 管理平台范围膨胀 → Mitigation: 一期只覆盖插件生命周期管理，不做复杂权限审批、审计报表和运行监控大盘。
- [Risk] 开源框架参考过多导致架构摇摆 → Mitigation: 逐模块评估“直接复用 / 参考设计 / 暂不采用”，不整体替换为单一框架。

## Migration Plan

1. 保持 `src_deepagent` 不变，所有新增实现进入 `plugin-platform/`。
2. 基于 OpenSpec 先实现平台工作区、manifest schema、CLI 和 backend skeleton。
3. 使用 example plugin 验证 validate/package/publish/install/enable/capability index。
4. 增加 Admin Console 基础页面，调用 backend API 完成同一链路。
5. 后续创建单独变更，把当前 Agent 作为外部消费者接入 capability discovery/invocation API。

回滚策略：由于不改现有 Agent 主链路，删除或停止 `plugin-platform/` 服务即可回退，不影响当前系统。

## Open Questions

- 生产 Registry 最终接内部制品仓库、对象存储还是数据库 BLOB，需要结合公司基础设施确定。
- workspace/agent/IAM 的真实模型和接口需要后续从公司平台侧确认。
- Admin Console 是否复用公司后台框架，还是先以本仓库 Vite 管理台独立开发，需要在进入前端详细实现前确认。
