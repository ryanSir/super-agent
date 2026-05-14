# 08. Claude Code 插件机制分析

## 目标

本文补充分析 Claude Code 的扩展机制，重点回答它对我们 Plugin 平台设计的启发，而不是重复评估 Claude Code CLI 是否适合作为沙箱执行引擎。

已有对比文档 `doc-component/agent-execution-engine-comparison.md` 结论是：Claude Code CLI 功能完整，但作为沙箱执行引擎时上下文和成本开销偏高。本文关注另一件事：Claude Code 如何组织 skills、MCP、commands、hooks、agents、settings 等能力，以及这些设计如何映射到我们的 Plugin 核心服务、管理平台和 Runtime Host。

参考资料：

- Claude Code overview: https://docs.anthropic.com/en/docs/claude-code/overview
- Claude Code settings: https://docs.anthropic.com/en/docs/claude-code/settings
- Claude Code MCP: https://docs.anthropic.com/en/docs/claude-code/mcp
- Claude Code slash commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- Claude Code hooks: https://docs.anthropic.com/en/docs/claude-code/hooks
- Claude Code subagents: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude Code plugins: https://code.claude.com/docs/en/plugins

## 一句话结论

Claude Code 的扩展体系是“本地 Agent 客户端扩展模型”：通过项目目录、用户目录、插件目录和 marketplace 安装，把 Skill、MCP、Slash Command、Hook、Subagent、LSP、Background Monitor、Setting 等能力加载进 Claude Code 本地运行环境。

它证明了一个重要判断：插件不应该被理解成单一 tool 或单一 MCP server，而应是一个可安装的能力包。但 Claude Code 的模型偏个人/项目本地使用，我们的目标是企业 Agent 平台，所以需要额外建设服务化治理能力：workspace/agent 级启用、凭据隔离、权限审计、统一调用网关、Runtime Host 和管理后台。

## Claude Code 的能力组成

Claude Code 不是只靠 MCP 扩展，它把多类能力组合在同一套本地扩展体系中。官方 plugin 文档中，一个插件可以包含 `.claude-plugin/plugin.json`、`skills/`、`agents/`、`hooks/`、`.mcp.json`、`.lsp.json`、`monitors/`、`bin/` 和 `settings.json` 等组件。

| 能力 | Claude Code 中的含义 | 对我们设计的映射 |
| --- | --- | --- |
| Skills | 领域能力说明、流程、约束和可附带资源 | Skill Plugin / Skill Context API |
| MCP servers | 接入外部工具和数据源 | MCP Plugin / MCP Runtime |
| Slash commands / commands | 用户显式触发的命令入口；新插件更推荐用 `skills/` 表达 | Command Plugin / 后续 Workflow 或快捷入口 |
| Hooks | 工具调用、提示词提交、会话等生命周期事件上的脚本 | Lifecycle Hook / Policy / Audit / Trigger 的参考 |
| Subagents | 带独立 system prompt、工具权限和上下文窗口的专用 Agent | Agent Template / Agent Strategy 的参考，但第一版不建议纳入 Plugin 主范围 |
| LSP servers | 为代码理解提供语言服务能力 | Code Intelligence Plugin / 后续 IDE 能力参考 |
| Background monitors | 后台监听日志、文件或外部状态，并向 Claude 发送通知 | Trigger / Monitor / Event Source 的参考 |
| `bin/` executables | 插件启用时加入 Bash PATH 的可执行命令 | Native Tool / Runtime Host 参考 |
| Settings | 权限、工具、模型和运行参数配置 | Plugin enable/config/policy 的客户端化参考 |
| Marketplace / Plugins | 可分发安装的能力集合 | Plugin Registry / Marketplace |

这一点和我们当前设计一致：Plugin 是能力包和治理单元，内部可以携带 Skill、MCP、工具、配置、Hook、UI 或资源，而不是某一种协议本身。

## Claude Code 的运行边界

Claude Code 的运行边界可以概括为：

```text
Claude Code CLI / 本地 Agent Runtime
  -> 读取项目级和用户级配置
  -> 加载 Skills / Commands / Subagents / Hooks / MCP / LSP / Monitors
  -> 根据权限策略决定可用工具
  -> 在本地进程中执行文件、Shell、MCP、Hook、Monitor 等能力
  -> 将结果回填给模型继续推理
```

这和我们的平台边界不同：

```text
业务 Agent 系统
  -> Plugin 核心服务
     -> Capability Resolver
     -> Policy Engine
     -> Credential Broker
     -> Tool Invocation Gateway
  -> 按能力类型分流
     -> Skill Context API
     -> Remote MCP / OpenAPI / Data Source runtime
     -> Plugin Runtime Host
```

差异的本质是：Claude Code 把 Agent Runtime、配置加载、工具执行、权限策略和本地运行环境收在一个客户端里；我们需要把这些能力拆成可服务化、可审计、可多租户治理的组件。

## 值得借鉴的设计

### 1. 多层配置和作用域

Claude Code 区分项目级、用户级和企业/托管配置。这个思路值得吸收，但需要服务端化：

| Claude Code | 我们的平台化版本 |
| --- | --- |
| project settings | workspace / project 级插件启用 |
| user settings | user 级偏好和授权 |
| managed settings | tenant / enterprise policy |
| local permission rules | Policy Engine / IAM / RBAC / ABAC |

建议我们的 enable/config 模型从第一版就保留作用域字段：

```text
tenant_id
workspace_id
agent_id
user_id
environment
```

### 2. Skills 作为轻量能力

Claude Code 的 Skill 更接近“能力说明 + 工作流知识 + 可选资源”，不是必须运行在独立 runtime 里的代码。这个设计可以强化我们的判断：

- Skill 第一版不需要进入 Runtime Host。
- Plugin 核心服务提供 Skill Context API 即可。
- 业务 Agent 在构造 system prompt 或 agent context 时注入授权后的 Skill。
- Skill 可以引用工具、MCP 或数据源，但自身不等于工具执行。

### 3. MCP 是工具协议，不是 Plugin 本身

Claude Code 支持 MCP server，但 MCP 只是扩展体系的一部分。这个判断和我们报告一致：

- Plugin 可以携带 MCP 配置。
- MCP runtime 可以是 remote service，也可以是 stdio adapter。
- stdio MCP 才是 Runtime Host 的重点场景。
- HTTP/Streamable MCP 可以优先由 Plugin 核心服务通过 Gateway 调用。

### 4. Hooks 给治理链路提供参考

Claude Code hooks 说明了用户和平台需要在关键生命周期点插入逻辑，例如工具调用前后、提示词提交、会话结束等。

我们不应直接照搬本地脚本式 hooks，但可以吸收事件模型：

| Claude Code hook 场景 | 我们的平台化能力 |
| --- | --- |
| PreToolUse | Policy Engine、敏感操作拦截、人审 |
| PostToolUse | Audit、结果脱敏、观测上报 |
| UserPromptSubmit | Prompt policy、上下文注入、合规检查 |
| Stop / SubagentStop | Runtime event、任务结束审计 |
| Notification | Admin Console / Webhook / Trigger |

第一版建议把 hooks 先收敛为平台内部事件和审计点，不开放任意脚本执行。二期再评估受控 lifecycle hook 或 trigger plugin。

### 5. Subagents 是强能力，但不宜过早插件化

Claude Code subagents 支持专用 system prompt、工具权限和独立上下文。它适合本地 Agent 工作流，但在企业平台里会带来复杂治理问题：

- 谁能安装和启用 subagent。
- subagent 可以使用哪些工具和数据。
- subagent 与主 Agent 的权限如何继承或收窄。
- subagent 调用是否单独计费、审计和观测。
- subagent 是否能继续创建子任务。

所以我们的报告中暂不纳入 `Agent Strategy Plugin` 是合理的。可以把 Claude Code subagents 作为二期 Agent Template / Team Agent 的参考，而不是 MVP Plugin 主能力。

### 6. LSP 和 Background Monitors 是有价值的二期参考

Claude Code plugin 还支持 LSP servers 和 background monitors：

- LSP servers 让 Claude Code 获得更强的代码智能能力，例如语言语义、定义跳转、诊断等。
- Background monitors 可以监听日志、文件或外部状态，并把事件作为通知送回 Claude Code 会话。

这两个能力不建议进入我们的 Plugin MVP，但值得作为二期方向：

- LSP 更适合归入代码智能或 IDE/Repo Agent 能力，不应和通用业务插件混在第一版。
- Monitors 更接近 Trigger/Event Source，需要配合权限、资源限制、生命周期管理和审计。
- 如果 monitor 执行长期命令或本地 watcher，应由 Runtime Host 或独立 worker 托管，而不是业务 Agent 主进程直接启动。

## 不建议直接照搬的部分

| Claude Code 做法 | 不直接照搬的原因 | 我们的替代方案 |
| --- | --- | --- |
| 本地 CLI 直接加载插件和配置 | 缺少企业服务端统一治理边界 | Plugin 核心服务 + 管理平台 |
| 本地文件配置承载权限 | 难满足 workspace/agent/user 多租户授权 | 数据库存储 enable/config/policy |
| Hook 执行本地脚本 | 安全风险高，审计和隔离成本大 | 平台事件、受控 policy、后续受限 hook runtime |
| CLI 直接管理 MCP server | 不适合多业务 Agent 共享和统一运维 | MCP Runtime + Credential Broker + Gateway |
| Subagent 作为本地配置扩展 | 企业权限和成本边界复杂 | 二期 Agent Template / Team Agent 能力 |
| LSP / monitor 由本地 CLI 启动 | 长驻进程和资源边界需要治理 | 二期 Runtime Host / worker / code intelligence service |

## 对当前 Plugin 平台设计的修正建议

### 1. 在开源参考中补充 Claude Code

当前报告已参考 Codex Plugins、Dify plugin daemon、Open WebUI、mcpo、n8n 等，但缺少 Claude Code。建议把 Claude Code 加为“强产品形态参考”，重点参考：

- Skill / command / MCP / hook / subagent 的组合扩展模型。
- LSP / monitor / bin / settings 的插件目录组织方式。
- 项目级、用户级、托管级配置分层。
- 插件市场和安装体验。
- 权限配置与工具启用体验。

### 2. manifest 预留 command、hook、agent 字段

MVP 不必实现所有能力，但 manifest 可以预留扩展方向：

```yaml
capabilities:
  skills: []
  tools: []
  mcp: []
  openapi: []
  data_sources: []
  commands: []   # 二期
  hooks: []      # 二期，必须受控
  agents: []     # 二期/三期，谨慎
  monitors: []   # 二期，长驻任务需 Runtime Host/worker 托管
  lsp: []        # 代码智能场景再评估
```

### 3. Runtime Host 继续保持窄定位

Claude Code 把本地执行能力放在 CLI 内部。我们不能把业务 Agent 主进程变成类似 Claude Code 的本地执行器，否则会回到插件依赖冲突和故障扩散的问题。

建议仍坚持：

- Skill、command 描述、远程 HTTP MCP / OpenAPI 不必进入 Runtime Host。
- stdio MCP、本地代码插件、受控 hooks、monitors、长任务 worker 才进入 Runtime Host。
- Runtime Host 是执行宿主，不是业务编排层。

### 4. Plugin 核心服务承担 Claude Code 中“本地权限配置”的服务端版本

Claude Code 的权限和工具启用更多发生在本地配置中。我们的平台需要把它服务化：

```text
本地 settings / permissions
  -> Plugin Manager enable/config
  -> Capability Index
  -> Policy Engine
  -> Credential Broker
  -> Audit
```

这也是为什么不能只让业务 Agent 自己接 MCP/API：一旦业务 Agent 各自接入，平台就失去统一授权、凭据和审计入口。

## 对比总结

| 维度 | Claude Code | 我们的平台 |
| --- | --- | --- |
| 目标用户 | 开发者本地 CLI / 项目工作区 | 企业多业务 Agent |
| 插件形态 | 本地/项目级能力扩展 | 服务化、可安装、可授权、可观测能力包 |
| 配置位置 | 文件和本地/托管 settings | 数据库、Registry、Admin Console、Policy |
| Skill | 本地加载进 Agent 上下文 | Skill Context API，按 workspace/agent 授权 |
| MCP | CLI 直接管理连接 | MCP Runtime / Gateway / Credential Broker |
| Hook | 本地生命周期脚本 | 平台事件、Policy、Audit，后续受控 hook |
| Subagent | 本地专用 Agent 配置 | 二期 Agent Template / Team Agent 参考 |
| LSP | 本地语言服务插件 | 二期 Code Intelligence 能力参考 |
| Monitor | 本地后台监听进程 | 二期 Trigger / Event Source / Runtime worker |
| Runtime | CLI 内置本地执行环境 | Runtime Host / remote service / sidecar / container |
| 治理 | 本地权限 + 企业托管配置 | tenant/workspace/agent/user 权限、审计、观测 |

## 最终判断

Claude Code 对我们的最大价值不是“可以复用它的 runtime”，而是证明了插件平台应该支持多能力组合：

- Skill 负责让 Agent 学会怎么做。
- MCP/OpenAPI/Data Source 负责让 Agent 能调用外部能力。
- Command 提供用户可显式触发的入口。
- Hook/Policy 提供生命周期治理点。
- Subagent 提供未来专业 Agent 模板方向。
- LSP/Monitor 提供代码智能和事件驱动方向。
- Marketplace/Plugin 把这些能力打包、安装、启用和分发。

但 Claude Code 是本地 Agent 客户端模型。我们的企业平台不能直接照搬它的本地文件配置和 CLI runtime，而应吸收其能力组织方式，并用 Plugin 核心服务、管理平台、Credential Broker、Policy Engine、Gateway、Runtime Host 完成服务化治理。
