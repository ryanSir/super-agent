# Plugin Platform Runbook

本文说明 `plugin-platform/` 当前目录和泳道图、系统边界、部署单元的对应关系，以及本地如何测试和启动完整链路。

## 1. 泳道图到系统边界

按之前的泳道图，Plugin 平台不是一个简单 backend，而是至少分成五条泳道：

```text
开发侧
  -> 编写插件
  -> plugin developer sdk / cli
  -> validate / package / publish

平台管理泳道
  -> Registry 存储插件包
  -> Plugin Manager 安装 / 启用 / 绑定 workspace 或 agent

Plugin 核心服务泳道
  -> Capability Index / Discovery
  -> Policy Check
  -> Credential Resolve / Injection
  -> Tool Invocation Gateway

插件运行时服务泳道
  -> Skill Context Runtime
  -> OpenAPI Runtime
  -> Streamable HTTP MCP Runtime
  -> 后续 Runtime Host

外部依赖泳道
  -> DB / Object Storage / 制品仓库
  -> IAM / Policy 系统
  -> Secret Manager
  -> 外部 API / MCP Server
  -> Observability / Langfuse

管理后台泳道
  -> Admin Console 查看插件
  -> 安装 / 启用 / 禁用
  -> 查看 capability index
```

当前阶段重点是把开发侧、平台管理面、Plugin 核心服务的 Capability 主链路和管理后台骨架先跑通。插件运行时服务现在只做远程运行边界，不做独立 Runtime Host。当前 `src_deepagent` Agent 集成后置。

## 2. 系统和部署单元

当前代码已经按泳道和未来部署单元重构，不再使用单一 `backend/plugin_platform/` 包承载所有模块。目录结构如下：

```text
plugin-platform/
  developer-tools/
    cli/
    sdk/

  services/
    plugin-management-service/
      registry/
      manager/
      storage/

    plugin-core-service/
      capability/
      policy/
      credential/
      gateway/
      api/

    plugin-runtime-service/
      openapi/
      streamable-mcp/
      skill-context/
      runtime-host/        # 后续

  admin-console/

  packages/
    plugin-contracts/      # manifest、capability、API DTO 等共享契约

  examples/
```

这样目录一眼就能看出来：

- `developer-tools/` 是开发侧，不是服务端 backend。
- `plugin-management-service/` 是平台管理面。
- `plugin-core-service/` 是 Agent / Admin / 管理面都会依赖的核心能力服务。
- `plugin-runtime-service/` 是运行时执行边界，第一阶段可以不独立部署。
- `packages/plugin-contracts/` 放共享模型，避免把领域模型塞进某个服务导致跨服务依赖倒置。

| 系统 / 部署单元 | 当前目录 | 生产形态 | 对应泳道 | 当前状态 |
| --- | --- | --- | --- | --- |
| Plugin Developer CLI / SDK | `developer-tools/cli/` + `developer-tools/sdk/` | 开发者本地工具或 CI 工具 | 开发侧 | 已实现 validate / package / publish client |
| 平台管理面 | `services/plugin-management-service/` | 可先和核心服务同进程部署，后续拆 Registry Service / Manager Service | 平台管理泳道 | 已实现 Registry、Manager、本地 dev store |
| Plugin 核心服务 | `services/plugin-core-service/` | 一期可以和管理面同进程部署，后续可独立为 Plugin Core Service | Plugin 核心服务泳道 | 已实现 Capability Discovery；Policy / Credential / Gateway 仅有边界，尚未完整落地 |
| 插件运行时服务 | `services/plugin-runtime-service/` | 一期不独立部署；后续可拆 Invocation Gateway / Runtime Host | 插件运行时服务泳道 | 已实现 OpenAPI、Streamable HTTP MCP、Skill Context 的轻量 runtime adapter |
| Admin Console | `admin-console/` | 独立前端应用 | 管理后台泳道 | 已实现管理台骨架 |
| Plugin Package / 示例插件 | `examples/plugins/` | 插件包、模板、测试样例 | 开发侧 | 已实现 `research-assistant` 示例插件 |
| 共享契约包 | `packages/plugin-contracts/` | Python package 或后续多语言契约包 | 横向共享 | 已实现 manifest、capability、validation result 等共享模型 |
| 外部依赖 | 当前用本地文件和外部 HTTP endpoint 占位 | DB、对象存储、制品仓库、IAM、Secret Manager、Langfuse、外部 API / MCP Server | 外部依赖泳道 | 第一阶段未接真实公司基础设施 |
| OpenSpec / 文档 | `../openspec/changes/build-production-plugin-platform/`、`../doc-plugin/` | 设计和验收资料 | 横向治理 | 不部署，只约束实现 |

第一阶段建议部署关系：

```text
Plugin Developer CLI / SDK
  -> HTTP publish

Plugin Backend
  -> 平台管理面：Registry / Manager
  -> Plugin 核心服务：Capability Discovery / Policy / Credential / Gateway 边界
  -> 插件运行时边界：OpenAPI / Streamable HTTP MCP / Skill Context

Admin Console
  -> HTTP 管理 API

外部依赖
  <- Plugin Backend 后续接入

后续：
Business Agent
  -> HTTP capability discovery / invocation
Plugin 核心服务
```

也就是说，`developer-tools/cli/` 不应该部署成常驻服务；`admin-console/` 是独立前端；`services/plugin-management-service/`、`services/plugin-core-service/`、`services/plugin-runtime-service/` 当前可以同进程启动，但代码目录已经按未来拆分边界分开。

## 3. Plugin 核心服务当前落地情况

设计里的 Plugin 核心服务应包含：

| 核心服务模块 | 设计职责 | 当前实现位置 | 当前状态 |
| --- | --- | --- | --- |
| Capability | 生成和查询 workspace / agent 可用能力 | `services/plugin-management-service/.../capability_index.py`、`services/plugin-core-service/.../capability_routes.py` | 已实现 |
| Policy | 调用前权限检查、scope 校验、策略决策 | 暂未单独落目录 | 后置，只在设计中保留 |
| Credential | 凭据解析、脱敏展示、调用时注入 | `examples/plugins/.../credentials/` 只有声明示例 | 后置，尚未实现 Broker |
| Gateway | 统一调用入口、错误归一、分流到 OpenAPI / MCP / Skill | `services/plugin-runtime-service/` 和后续 Plugin Core API 边界 | 部分实现 runtime adapter，尚未形成完整 Invocation Gateway API |

因此，现在不是没有 Plugin 核心服务，而是第一阶段只完成了 Capability 主线和运行时 adapter。Policy、Credential、完整 Gateway 会在后续阶段补齐。

## 4. 当前目录和设计模块对应关系

### 4.1 顶层目录

| 目录 / 文件 | 对应系统 | 对应设计模块 | 说明 |
| --- | --- | --- | --- |
| `README.md` | 文档入口 | 平台边界说明 | 说明 Plugin 平台是独立工作区，不属于当前 `src_deepagent` Agent 代码 |
| `RUNBOOK.md` | 文档入口 | 运行和测试手册 | 当前文件 |
| `developer-tools/` | Plugin Developer CLI / SDK | Developer Lifecycle | 插件开发者本地命令和 SDK |
| `services/plugin-management-service/` | 平台管理面 | Registry / Plugin Manager / Storage | 发布、安装、启用、禁用、绑定 |
| `services/plugin-core-service/` | Plugin 核心服务 | Capability / Policy / Credential / Gateway API | 当前实现 Capability Discovery 和 API 聚合入口 |
| `services/plugin-runtime-service/` | 插件运行时服务 | OpenAPI / Streamable HTTP MCP / Skill Context | 当前是轻量 adapter，后续可拆运行时服务 |
| `packages/plugin-contracts/` | 共享契约包 | Manifest / Schema / Capability Model | 避免服务之间反向依赖 |
| `admin-console/` | Admin Console | Plugin 管理平台 | 管理员使用的前端 |
| `examples/plugins/` | Plugin Package | 插件包结构示例 | 用于测试完整链路 |

### 4.2 Python 包和模块

当前 Python 包按部署边界拆分：

| Python 包 | 所在目录 | 对应设计模块 | 说明 |
| --- | --- | --- | --- |
| `plugin_contracts` | `packages/plugin-contracts/` | Manifest / Schema / Capability Model | `plugin.yaml`、capability、validation result 等核心模型 |
| `plugin_developer` | `developer-tools/sdk/` | Developer SDK | 插件校验、打包、发布客户端逻辑 |
| `plugin_management_service` | `services/plugin-management-service/` | Registry / Manager / Storage | 插件包版本、安装启用状态、Capability Index |
| `plugin_core_service` | `services/plugin-core-service/` | Plugin Core API | FastAPI app、管理 API、Capability Discovery API |
| `plugin_runtime_service` | `services/plugin-runtime-service/` | Runtime Adapter | OpenAPI、Streamable HTTP MCP、Skill Context 运行边界 |
| `tests/` | `tests/` | Verification | 单测、API 流程测试、runtime adapter 测试 |

如果将来要拆服务，优先拆分顺序建议是：

```text
Plugin Backend 单体
  -> Registry Service
  -> Plugin Manager Service
  -> Plugin Core Service：Capability / Policy / Credential / Gateway
  -> Invocation Gateway
  -> Runtime Host
  -> Audit / Observability Service
```

对应 OpenSpec 变更：

- `openspec/changes/build-production-plugin-platform/`
- 其中 `proposal.md` 说明为什么做，`design.md` 说明架构决策，`specs/` 说明行为要求，`tasks.md` 记录实现任务。

## 5. 环境准备

在仓库根目录执行：

```bash
cd /Users/zhangyang/Desktop/temp/super-agent
```

后端依赖沿用当前 Python 环境。前端依赖已经安装在：

```text
plugin-platform/admin-console/node_modules/
```

如果后续重新拉取代码，需要重新安装：

```bash
npm --prefix plugin-platform/admin-console install
```

CLI 和 `uvicorn` 从仓库根目录运行时，需要设置 Python import path：

```bash
export PLUGIN_PLATFORM_PYTHONPATH="plugin-platform/packages/plugin-contracts:plugin-platform/developer-tools/sdk:plugin-platform/services/plugin-management-service:plugin-platform/services/plugin-core-service:plugin-platform/services/plugin-runtime-service"
```

## 6. 后端测试

运行全部后端测试：

```bash
python -m pytest plugin-platform/tests
```

当前覆盖：

- manifest 校验成功。
- 缺失引用文件时报错。
- `stdio` MCP 在第一阶段被拒绝。
- 插件打包成功和校验失败中断打包。
- Registry 重复版本冲突。
- Plugin Manager 安装、启用、禁用、agent 绑定。
- Capability Index 查询。
- Backend API 的 publish -> install -> enable -> discover 主流程。
- OpenAPI timeout 结构化错误。
- Streamable HTTP MCP JSON / SSE 响应处理。
- Skill Context 不允许作为可执行 tool 调用。

## 7. CLI 测试

校验示例插件：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py validate \
  plugin-platform/examples/plugins/research-assistant
```

打包示例插件：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py package \
  plugin-platform/examples/plugins/research-assistant \
  --out /tmp/plugin-platform-packages
```

成功后会生成类似：

```text
/tmp/plugin-platform-packages/research-assistant-0.1.0.zip
```

## 8. 启动完整链路

完整链路包含：

```text
开发插件
  -> validate
  -> package
  -> 启动 Registry / Manager Backend
  -> publish
  -> Admin Console 查看插件
  -> install
  -> enable
  -> capability discovery
```

### 8.1 启动 Plugin Core API

在仓库根目录执行：

```bash
plugin-platform/scripts/run-backend.sh
```

Backend 地址：

```text
http://127.0.0.1:8017
```

### 8.2 打包并发布示例插件

另开一个终端，在仓库根目录执行：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py package \
  plugin-platform/examples/plugins/research-assistant \
  --out /tmp/plugin-platform-packages
```

发布到本地 Registry：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py publish \
  /tmp/plugin-platform-packages/research-assistant-0.1.0.zip \
  --registry-url http://127.0.0.1:8017
```

查看 Registry：

```bash
curl http://127.0.0.1:8017/api/registry/plugins
```

### 8.3 启动 Admin Console

另开一个终端：

```bash
plugin-platform/scripts/run-admin-console.sh
```

默认访问：

```text
http://127.0.0.1:5177
```

前端 Vite 已配置代理：

```text
/api -> http://127.0.0.1:8017
```

打开页面后可以看到：

- Registry 插件列表。
- 插件详情。
- capability 列表。
- Install 操作。
- Enable / Disable 操作。
- workspace capability index。

### 8.4 用 API 直接验证 install / enable / discovery

安装插件到 workspace：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations \
  -H 'Content-Type: application/json' \
  -d '{"workspace_id":"workspace-1","plugin_id":"research-assistant","version":"0.1.0"}'
```

启用插件：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations/enable \
  -H 'Content-Type: application/json' \
  -d '{"workspace_id":"workspace-1","plugin_id":"research-assistant"}'
```

查询 workspace 能力：

```bash
curl -sS http://127.0.0.1:8017/api/capabilities/workspaces/workspace-1
```

绑定给指定 agent：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations/bind-agent \
  -H 'Content-Type: application/json' \
  -d '{"workspace_id":"workspace-1","plugin_id":"research-assistant","agent_id":"agent-1"}'
```

查询 agent 级能力：

```bash
curl -sS http://127.0.0.1:8017/api/capabilities/workspaces/workspace-1/agents/agent-1
```

## 9. 构建验证

后端：

```bash
python -m pytest plugin-platform/tests
```

前端：

```bash
npm --prefix plugin-platform/admin-console run build
```

OpenSpec 状态：

```bash
openspec status --change build-production-plugin-platform --json
```

## 10. 当前阶段边界

已实现：

- 独立 Plugin 平台目录。
- `plugin.yaml` 最小生产 schema。
- validate / package / publish。
- Registry / Manager / Capability Index。
- Backend API。
- Admin Console 骨架。
- OpenAPI / Streamable HTTP MCP / Skill Context runtime 边界。

暂未实现：

- 当前 `src_deepagent` Agent 集成。
- 公司 IAM / RBAC / ABAC。
- Credential Broker 和真实密钥系统。
- 完整 Policy Engine。
- 审计留存和 Langfuse trace。
- stdio MCP adapter。
- Runtime Host。
- Workflow / Trigger / App/UI / Agent Strategy Plugin。

下一阶段建议先补生产级存储、Credential / Policy 细化和管理台状态持久化，然后再单独开 OpenSpec 做当前 Agent 接入。
