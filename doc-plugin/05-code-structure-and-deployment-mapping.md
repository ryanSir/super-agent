# Plugin POC 代码分层与部署映射

当前 POC 代码已按端到端泳道图和未来部署边界做分层。目录结构不是最终生产形态，但已经能表达哪些模块属于开发工具、管理面、Plugin 核心服务、Runtime Host 和具体 runtime。

配套图：

- [端到端流程说明](./03-plugin-end-to-end-flow.md)
- [端到端流程泳道图](./plugin-end-to-end-flow-swimlane.svg)

## 目录结构

```text
plugin_poc/
├── cli.py
├── developer_tooling/
├── management/
├── core/
├── runtime_host/
├── runtimes/
├── acceptance/
└── shared/
```

## 分层说明

| 目录 | 对应泳道 / 未来边界 | 职责 |
| --- | --- | --- |
| `developer_tooling/` | 开发侧：Plugin Developer / SDK / CLI | 插件校验、打包、发布，未来可演进为 Plugin SDK / CLI |
| `management/` | Plugin 管理平台 | 安装、启用、禁用、卸载、Capability Index |
| `core/` | Plugin 核心服务 | 权限、凭据、统一调用网关、审计、运行事件 |
| `runtime_host/` | Plugin Runtime Host | 插件 runtime 生命周期、健康检查、stdio adapter metadata |
| `runtimes/` | Plugin Runtime Host 内部 runtime | MCP、OpenAPI、Data Source、Skill runtime |
| `acceptance/` | 验收工具 | 本地 E2E 验收链路 |
| `shared/` | 共享基础库 | 错误、模型、文件 IO、checksum 等基础能力 |
| `cli.py` | POC 入口 | 聚合各层能力，模拟未来 API / 管理后台调用 |

## 文件归属

### 开发侧：`developer_tooling/`

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `validator.py` | 校验 `plugin.yaml` 和子配置引用 | Plugin SDK / CLI |
| `packager.py` | 生成 zip package、metadata、checksum | Plugin SDK / CLI |
| `publisher.py` | 发布插件到本地 Registry | Plugin SDK / CLI 或 Plugin 管理平台 |

### 管理面：`management/`

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `manager.py` | install / enable / disable / uninstall / list | Plugin 管理平台 |
| `capability.py` | 从 manifest 构建 Capability Index | Plugin 管理平台 / Plugin 核心服务共享 |

### Plugin 核心服务：`core/`

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `gateway.py` | 统一 `invoke_capability` 调用入口 | Plugin 核心服务 |
| `policy.py` | 凭据要求、敏感操作确认等最小策略 | Plugin 核心服务，后续接 IAM/RBAC/ABAC |
| `credentials.py` | 凭据配置、脱敏、test connection | Plugin 核心服务，后续接密钥系统 |
| `audit.py` | 调用审计 JSONL | Plugin 核心服务，后续写 DB / 审计平台 |
| `observability.py` | runtime events JSONL | Plugin 核心服务，后续接 Langfuse |

### Runtime Host：`runtime_host/`

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `host.py` | start / stop / health / stdio adapter metadata | 独立 Plugin Runtime Host 服务 |

### 具体 Runtime：`runtimes/`

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `mcp_runtime.py` | Streamable HTTP MCP `tools/list` 和 `tools/call` | Plugin Runtime Host |
| `openapi_runtime.py` | OpenAPI operation mock invocation | Plugin Runtime Host |
| `data_source_runtime.py` | local JSON data source query | Plugin Runtime Host 或数据平台 adapter |
| `skill_runtime.py` | `SKILL.md` 解析和 Agent context 渲染 | Plugin 核心服务或 Runtime Host，取决于最终 prompt 装配位置 |

### 验收与共享

| 文件 | 职责 | 未来可能归属 |
| --- | --- | --- |
| `acceptance/e2e.py` | 本地 E2E 验收 | 测试/验收工具 |
| `shared/errors.py` | 公共异常 | 共享基础库 |
| `shared/io.py` | YAML/JSON/checksum helper | 共享基础库 |
| `shared/models.py` | POC dataclass models | 共享基础库或各服务 DTO |
| `cli.py` | 命令行入口 | POC 聚合入口，生产化后拆成 API / Admin Console / SDK |

## 和未来服务的关系

第一版生产化建议按以下服务边界演进：

```text
业务 Agent 系统
  -> 调用 Plugin 核心服务

Plugin 核心服务
  -> core/
  -> 部分 management/capability.py
  -> 部分 runtimes/skill_runtime.py

Plugin 管理平台
  -> management/
  -> developer_tooling/publisher.py
  -> Registry / Marketplace / Admin Console

Plugin Runtime Host
  -> runtime_host/
  -> runtimes/

Plugin SDK / CLI
  -> developer_tooling/

共享基础库
  -> shared/
```

当前 POC 为了便于本地验证，所有模块都在同一个 Python package 里；生产化时可以按以上边界拆成服务或内部包。

## 为什么保留 `cli.py`

`cli.py` 不是未来服务边界的一部分，它只是 POC 的统一入口，用来模拟：

- 开发者 CLI
- 管理后台操作
- 业务 Agent 调用
- 运维验收命令

生产化后，这些入口会拆成：

- Plugin SDK / CLI
- Admin Console API
- Plugin Core Service API
- Runtime Host internal API
