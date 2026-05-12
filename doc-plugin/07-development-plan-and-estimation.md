# 07. Plugin 0-1 开发计划与粗估

## 目标

本文件给出 Plugin 系统从 0 到 1 的完整开发计划，覆盖插件开发、打包、注册、安装、启用、运行、Agent 调用、权限、凭据、审计和示例插件。

估时为 ROM 粗估，用于规划和资源判断，不作为最终排期承诺。最终排期需要在技术选型、MVP 范围、安全边界和现有平台复用能力确认后细化。

## 范围假设

第一版目标是做出企业内部可用的 Plugin MVP，不做开放生态完整 marketplace。

第一版包含：

- Plugin manifest schema
- Plugin package 格式
- Plugin SDK/CLI 基础能力
- Plugin Registry 基础能力
- Plugin Manager 安装、启用、禁用、升级、卸载
- Capability Index 能力索引
- Tool Invocation Gateway
- OpenAPI connector plugin
- Streamable HTTP MCP plugin
- stdio MCP adapter PoC
- Skill plugin
- Data Source plugin 基础接入
- Credential schema、加密存储、连接测试
- Policy check、敏感操作确认、audit log
- Observability 基础日志和 trace
- Admin Console 基础页面
- 2-3 个官方示例插件

第一版不包含：

- 外部开放 marketplace
- 插件商业化结算
- 完整 App/UI Plugin 沙箱
- 完整 Workflow / Trigger 系统
- Agent Strategy Plugin
- Model Provider Plugin
- 完整 serverless runtime
- 复杂灰度发布和多版本并行治理

## 端到端流程

```text
开发插件
  ↓
编写 plugin.yaml / 子配置
  ↓
plugin validate
  ↓
plugin package
  ↓
plugin publish
  ↓
Plugin Registry 存储插件包和版本
  ↓
管理员 install
  ↓
Plugin Manager 校验、解包、登记能力
  ↓
配置 credentials / test connection
  ↓
绑定 workspace / agent / user
  ↓
启用 plugin
  ↓
Plugin Runtime Host 准备运行实例
  ↓
Agent Runtime 通过 Capability Resolver 发现能力
  ↓
Policy Engine 检查权限
  ↓
Credential Broker 注入凭据
  ↓
Tool Invocation Gateway 调用插件能力
  ↓
Plugin Runtime Host 执行
  ↓
返回结构化结果
  ↓
Observability / Audit 记录调用
```

## 阶段计划

建议按 6 个阶段推进。

| 阶段 | 目标 | 粗估周期 |
| --- | --- | --- |
| Phase 0 | 技术选型和 PoC | 2-3 周 |
| Phase 1 | 插件规范、打包和 Registry | 2-3 周 |
| Phase 2 | Plugin Manager 和能力索引 | 2-3 周 |
| Phase 3 | Runtime Host 和调用网关 | 3-5 周 |
| Phase 4 | 凭据、权限、审计和管理界面 | 3-4 周 |
| Phase 5 | 示例插件、联调、测试和 MVP 验收 | 2-3 周 |

如果团队足够并行，MVP 粗估为 **10-14 周**。如果团队较小或安全隔离要求较高，粗估为 **14-18 周**。

## Phase 0：技术选型和 PoC

目标：在正式建设前确认关键技术路径，避免后续返工。

重点任务：

1. Runtime 运行形态选型
   - 对比 Local daemon、Remote service、Sidecar、Container、Serverless。
   - 第一版重点验证 `Local daemon + Remote service`。
   - 明确是否需要托管 stdio MCP。

2. MCP adapter PoC
   - 调研 `mcpo`。
   - 把一个 stdio MCP server 转成 HTTP/OpenAPI 或 Streamable HTTP 调用。
   - 验证 tool schema、调用结果、错误处理、超时和日志。

3. Dify plugin daemon 源码调研
   - 看 lifecycle、local/debug/serverless runtime。
   - 判断哪些设计可借鉴，哪些代码可复用。

4. Credential PoC
   - 参考 n8n credential schema。
   - 支持 API Key 和 OAuth2 的最小配置、加密存储、test connection。

交付物：

- Runtime 选型结论
- MCP adapter PoC 结果
- Dify plugin daemon 源码调研记录
- Credential schema PoC
- MVP 技术风险清单

粗估：2-3 周。

## Phase 1：插件规范、打包和 Registry

目标：定义插件如何写、如何校验、如何打包、如何发布到仓库。

### 1. Manifest schema

任务：

- 定义 `plugin.yaml` 字段。
- 定义 `plugin.schema.json`。
- 支持 capabilities、auth、permissions、runtime、policy、observability。
- 支持通过 `path` 引用 tools、skills、credentials、openapi、data_sources 子文件。
- 支持 schema version。

验收：

- `plugin validate` 能校验合法和非法 manifest。
- 错误信息能定位到具体字段。
- 子文件不存在或格式错误能被发现。

### 2. Plugin package 格式

建议第一版采用普通压缩包格式：

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

打包流程：

```text
plugin package
  ↓
读取 plugin.yaml
  ↓
校验 manifest 和子文件
  ↓
生成 package metadata
  ↓
计算 checksums
  ↓
生成 zip/tar.gz
  ↓
可选签名
```

第一版可以先支持 zip 包，二期再支持签名、SBOM、依赖锁定和安全扫描。

### 3. Plugin SDK / CLI

第一版命令：

```text
plugin init
plugin validate
plugin package
plugin publish
plugin install
plugin run
plugin debug
```

最低可用版本可以先实现：

```text
plugin init
plugin validate
plugin package
plugin publish
```

### 4. Plugin Registry

Registry 第一版职责：

- 存储插件包。
- 管理 plugin id、version、author、created_at。
- 管理 publish 状态。
- 支持查询插件列表和详情。
- 支持下载指定版本。
- 支持内部官方插件和团队插件。

核心数据：

```text
plugin_id
version
name
description
author
package_url
checksum
manifest_snapshot
status
created_at
updated_at
```

验收：

- CLI 可以 publish 插件。
- 管理端可以看到插件列表。
- Plugin Manager 可以从 Registry 拉取指定版本。

粗估：2-3 周。

## Phase 2：Plugin Manager 和能力索引

目标：让平台能安装、启用、禁用、升级插件，并把能力暴露给 Agent。

### 1. Plugin Manager

任务：

- install plugin
- uninstall plugin
- enable plugin
- disable plugin
- upgrade plugin
- bind plugin to workspace / agent
- 读取 manifest snapshot
- 校验平台版本兼容性
- 记录安装状态

核心状态：

```text
installed
configured
enabled
disabled
failed
upgrading
uninstalled
```

### 2. Capability Index

任务：

- 从 manifest 和子文件解析 capabilities。
- 登记 tools、skills、data_sources、mcp、openapi。
- 记录能力所属 plugin、version、workspace、agent、user。
- 记录能力需要的 permissions 和 credentials。
- 提供查询接口给 Capability Resolver。

能力索引示例：

```text
capability_id: company.jira.search_issues
plugin_id: company.jira
plugin_version: 1.0.0
type: tool
workspace_id: ws_001
agent_id: agent_001
permission_required: jira.issues.read
credential_required: jira_api_key
status: enabled
```

### 3. Capability Resolver

任务：

- 根据 agent、workspace、user 查询可用能力。
- 支持按能力类型过滤。
- 支持工具描述和 input schema 返回。
- 支持 skill 内容加载。

验收：

- 安装并启用插件后，Agent 可以发现对应 tools 和 skills。
- 禁用插件后，Agent 不再发现这些能力。
- 升级插件后，能力索引更新。

粗估：2-3 周。

## Phase 3：Runtime Host 和调用网关

目标：让 Agent 能真正调用插件能力。

### 1. Tool Invocation Gateway

任务：

- 提供统一 tool invocation API。
- 根据 capability_id 路由到 MCP Runtime、OpenAPI Runtime 或 native runtime。
- 做参数校验。
- 处理 timeout、retry、error mapping。
- 记录调用开始、结束、失败。

统一调用模型：

```json
{
  "capability_id": "company.jira.search_issues",
  "input": {
    "jql": "project = ABC"
  },
  "context": {
    "tenant_id": "tenant_001",
    "workspace_id": "ws_001",
    "agent_id": "agent_001",
    "user_id": "user_001"
  }
}
```

### 2. Plugin Runtime Host

第一版建议支持：

- Remote service runtime
- Local daemon runtime PoC

Remote service runtime：

- 插件能力由远程 HTTP/MCP 服务承载。
- 平台负责鉴权、超时、日志和结果标准化。

Local daemon runtime：

- daemon 负责启动、停止、健康检查、本地插件进程。
- 优先用于 MCP stdio、本地调试和部分内部插件。

### 3. OpenAPI Runtime

任务：

- 解析 OpenAPI spec。
- 生成 tool schema。
- operation allowlist。
- 参数校验。
- HTTP 调用。
- credential 注入。
- 错误码归一。

### 4. MCP Runtime

任务：

- 支持 Streamable HTTP MCP。
- 兼容老版 HTTP+SSE MCP。
- stdio MCP 通过 adapter 或 daemon 托管。
- 发现 MCP tools。
- 调用 MCP tools。
- 归一化 MCP 结果。

验收：

- Agent 可以调用 OpenAPI connector tool。
- Agent 可以调用 Streamable HTTP MCP tool。
- stdio MCP PoC 可以通过 adapter 被调用。
- 插件异常不影响 Agent 主进程。
- 调用结果、错误、耗时能被记录。

粗估：3-5 周。

## Phase 4：凭据、权限、审计和管理界面

目标：让插件可被企业安全使用。

### 1. Credential Broker

任务：

- 支持 credential schema。
- 支持 API Key、Bearer Token、OAuth2 基础模式。
- 凭据加密存储。
- 凭据按 tenant/workspace/user 隔离。
- test connection。
- 调用时按需注入凭据。
- 凭据不进入模型上下文。

### 2. Policy Engine

任务：

- 校验 plugin permission。
- 校验 user/workspace/agent 是否被授权。
- 支持 read/write/sensitive action。
- 敏感操作支持用户确认。
- 支持基础 allow/deny 策略。

### 3. Audit Log

审计字段：

```text
tenant_id
workspace_id
agent_id
user_id
plugin_id
plugin_version
capability_id
operation
input_summary
output_summary
status
error_code
duration_ms
created_at
```

### 4. Admin Console

第一版页面：

- Plugin 列表
- Plugin 详情
- 安装/启用/禁用
- 版本查看
- Credential 配置
- Test connection
- Workspace/Agent 绑定
- 调用日志查看

验收：

- 管理员可以安装和启用插件。
- 管理员可以配置凭据并测试连接。
- Agent 调用插件前会经过权限检查。
- 敏感操作可以触发确认。
- 所有调用有审计记录。

粗估：3-4 周。

## Phase 5：示例插件、联调、测试和 MVP 验收

目标：用真实插件验证完整链路。

建议示例：

1. Jira 或飞书 API Connector Plugin
   - 验证 OpenAPI、credential、tool invocation、audit。

2. GitHub 或 filesystem MCP Plugin
   - 验证 MCP Runtime、adapter、tool schema。

3. 周报生成 Skill Plugin
   - 验证 skill 发现、加载和 Agent 使用方式。

测试范围：

- manifest schema 测试
- package 校验测试
- registry publish/download 测试
- install/enable/disable/upgrade 测试
- capability resolver 测试
- OpenAPI tool invocation 测试
- MCP tool invocation 测试
- credential 注入测试
- policy 拦截测试
- audit log 测试
- admin console e2e 测试
- 插件异常和超时测试

MVP 验收标准：

- 开发者能创建、校验、打包、发布一个插件。
- 管理员能从 Registry 安装、配置、启用插件。
- Agent 能发现插件暴露的 tools/skills。
- Agent 能调用至少一个 OpenAPI tool 和一个 MCP tool。
- 凭据不进入模型上下文。
- 权限检查和 audit log 生效。
- 插件失败不会影响 Agent 主进程。
- 至少 2 个官方示例插件跑通端到端链路。

粗估：2-3 周。

## 角色与人力建议

MVP 推荐团队：

| 角色 | 建议人数 | 主要职责 |
| --- | --- | --- |
| Tech Lead / 架构 | 1 | 总体架构、关键技术选型、评审和风险收敛 |
| 后端/平台工程 | 3-4 | Registry、Manager、Runtime、Gateway、Credential、Policy |
| 前端工程 | 1-2 | Admin Console、插件配置、凭据表单、日志页面 |
| QA / 测试 | 1 | E2E、权限、异常、回归测试 |
| DevOps / SRE | 0.5-1 | Runtime 部署、日志、监控、资源隔离 |
| 安全工程 | 0.5 | 权限、凭据、审计、安全评估 |

最低配置：

```text
Tech Lead 1
后端 3
前端 1
QA 1
DevOps/Security 兼职
```

较稳配置：

```text
Tech Lead 1
后端 4
前端 2
QA 1
DevOps 1
Security 0.5
```

## 粗估汇总

| 模块 | 复杂度 | 粗估 |
| --- | --- | --- |
| 技术选型和 PoC | M | 2-3 周 |
| Manifest schema + validator | M | 1-2 周 |
| Plugin package + CLI | M | 2-3 周 |
| Plugin Registry | M | 2-3 周 |
| Plugin Manager | L | 2-3 周 |
| Capability Index / Resolver | M | 1-2 周 |
| Tool Invocation Gateway | L | 2-3 周 |
| OpenAPI Runtime | L | 2-3 周 |
| MCP Runtime / adapter | L/XL | 3-5 周 |
| Credential Broker | L | 2-3 周 |
| Policy + Audit | L | 2-3 周 |
| Admin Console | M/L | 3-4 周 |
| 示例插件 | M | 2-3 周 |
| 联调和验收 | L | 2-3 周 |

并行后整体 MVP 粗估：

```text
乐观：10-12 周
正常：12-14 周
保守：14-18 周
```

影响估时的主要变量：

- 是否直接复用或 fork `mcpo`。
- 是否需要托管 stdio MCP。
- Credential 是否要完整 OAuth2 refresh。
- Policy 是否接入公司现有权限系统。
- Registry 是否已有制品仓库可复用。
- Admin Console 是否已有后台框架。
- Runtime 隔离要求是进程级、容器级还是租户级。

## 并行开发建议

可以并行推进的工作流：

```text
工作流 A：规范和 SDK
Manifest schema → validator → package → publish

工作流 B：平台管理
Registry → Plugin Manager → Capability Index

工作流 C：运行调用
Tool Gateway → OpenAPI Runtime → MCP Runtime → Runtime Host

工作流 D：安全治理
Credential Broker → Policy Engine → Audit Log

工作流 E：前端体验
Plugin list/detail → install/configure → credentials → logs

工作流 F：示例插件
OpenAPI example → MCP example → Skill example
```

关键依赖：

- `Capability Index` 依赖 manifest 和 Manager。
- `Tool Gateway` 依赖 capability schema。
- `Credential Broker` 和 `Policy Engine` 必须在真实调用前接入。
- 示例插件可以在 schema 稳定后提前启动。

## 主要风险

| 风险 | 影响 | 缓解方式 |
| --- | --- | --- |
| MCP stdio 托管复杂 | Runtime 复杂度上升 | 先做 adapter PoC，第一版优先 Streamable HTTP |
| 插件隔离不足 | 安全风险 | 禁止 in-process，优先 daemon/remote，后续容器化 |
| Credential 泄露 | 高安全风险 | 凭据只由 Broker 注入，不进入模型上下文 |
| Policy 后补困难 | 架构返工 | 第一版即纳入 read/write/sensitive 权限模型 |
| Registry 重复造轮子 | 开发周期变长 | 优先评估复用内部制品仓库 |
| OpenAPI 自动生成 tool 质量不稳定 | Agent 调用效果差 | 支持 operation allowlist 和人工描述增强 |
| Admin Console 低估 | 交付延迟 | 第一版只做安装、配置、启用、日志核心页面 |
| 开源复用 license 不清 | 法务和发布风险 | Phase 0 必做 license/security 检查 |

## 里程碑建议

| 里程碑 | 时间点 | 交付 |
| --- | --- | --- |
| M0 | 第 2-3 周 | 技术选型和 PoC 结论 |
| M1 | 第 4-5 周 | manifest、package、registry 初版 |
| M2 | 第 6-7 周 | install/enable、Capability Index 跑通 |
| M3 | 第 8-10 周 | OpenAPI/MCP 调用链路跑通 |
| M4 | 第 10-12 周 | Credential、Policy、Audit、Admin Console 初版 |
| M5 | 第 12-14 周 | 示例插件端到端验收，MVP release candidate |

## 当前建议结论

第一版建议采用：

```text
plugin.yaml + plugin.schema.json
zip package
internal Plugin Registry
Plugin Manager
Capability Index
Tool Invocation Gateway
Local daemon PoC + Remote service runtime
OpenAPI Runtime
Streamable HTTP MCP Runtime
Credential Broker
Policy + Audit
Admin Console
2-3 个官方示例插件
```

这条路径能覆盖从 0 到 1 的完整闭环，同时保留后续向 sidecar、container、serverless 和外部 marketplace 演进的空间。

