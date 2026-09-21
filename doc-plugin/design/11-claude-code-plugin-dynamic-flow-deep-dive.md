# 11. Claude Code Plugin 动态加载与执行链路深度分析

## 1. 分析目标

本文专项分析 Claude Code 的插件体系，重点拆解：

- Claude Code 如何管理 plugin marketplace、install scope、enable state 和缓存目录。
- plugin 启用后，skills、agents、hooks、MCP、LSP、monitors、themes、channels 如何进入 Claude Code 运行时。
- Agent 每轮会话中，skill、MCP、subagent、hook 分别在什么时间加载，加载多少上下文。
- Claude Code 如何通过 skill on-demand loading、MCP tool search、subagent isolated context、hook external execution 避免 token 膨胀。
- 这些机制对我们企业 Plugin 平台的设计启发。

说明：Claude Code 不是完整开源项目，本文不做源码级调用栈断言。文中“官方确认”来自 Claude Code 官方文档；“运行时推导”基于文档暴露的配置、CLI、生命周期、上下文加载行为和事件语义。

## 2. 一句话结论

Claude Code 的插件体系是一个“本地 Agent Runtime 扩展包模型”。Plugin 是分发和治理单元，不是单个可执行函数。一个 plugin 可以打包：

```text
skills / commands
agents
hooks
MCP servers
LSP servers
monitors
themes
output styles
channels
userConfig
dependencies
assets / metadata
```

Claude Code 的动态处理核心是：

```text
Plugin 安装到本地 cache
  -> settings.json 记录 marketplace 和 enabledPlugins
  -> session / reload 时扫描 enabled plugin
  -> 只把必要索引放入上下文
  -> skill 全文按需加载
  -> MCP tool schema 延迟到具体工具需要时加载
  -> subagent 用独立 context window
  -> hook 在外部执行，默认不占模型上下文
  -> monitor / LSP 作为事件和代码智能能力接入
```

对我们平台最重要的启发：

> 插件系统不能只做“工具注册表”，必须做“能力包生命周期 + 动态上下文装配 + 运行隔离 + 权限/凭据/审计”的组合。

## 3. Claude Code Plugin 能力模型

### 3.1 Plugin 是组件包

官方插件参考说明：plugin 是一个自包含目录，用来扩展 Claude Code。组件包括 skills、agents、hooks、MCP servers、LSP servers 和 monitors。

典型目录：

```text
my-plugin/
  .claude-plugin/
    plugin.json
  skills/
    <skill-name>/
      SKILL.md
      references/
      scripts/
  commands/
    <command>.md
  agents/
    <agent>.md
  hooks/
    hooks.json
  .mcp.json
  .lsp.json
  monitors/
    monitors.json
  themes/
  output-styles/
```

注意：

- `.claude-plugin/plugin.json` 是 manifest。
- 其他能力目录必须在 plugin root，不应放进 `.claude-plugin/`。
- manifest 是可选的。如果没有 manifest，Claude Code 会按默认路径自动发现组件，并用目录名推导 plugin name。

### 3.2 Plugin 和 standalone 配置的区别

Claude Code 支持两种扩展方式：

| 方式 | 位置 | 命名 | 适合场景 |
| --- | --- | --- | --- |
| standalone `.claude/` | 项目或用户配置目录 | `/hello` | 个人工作流、项目本地定制、快速实验 |
| plugin | `.claude-plugin/plugin.json` + plugin root | `/plugin-name:hello` | 团队共享、marketplace 分发、版本化、跨项目复用 |

Plugin skills 强制 namespaced，例如：

```text
/commit-commands:commit
/quality-review-plugin:quality-review
```

这个设计解决技能名冲突，也让模型和用户知道能力来自哪个插件。

## 4. Marketplace 与安装链路

### 4.1 Marketplace 是 catalog，不是 runtime

Claude Code marketplace 是插件目录，负责集中发现、版本追踪、更新和多种 source 支持。

支持来源：

```text
official marketplace: claude-plugins-official
GitHub repo: owner/repo
Git URL: https://gitlab.com/company/plugins.git
local directory
direct marketplace.json file
remote marketplace.json URL
seed directory for container / CI
managed marketplace
```

添加 marketplace：

```text
/plugin marketplace add anthropics/claude-code
/plugin marketplace add https://gitlab.com/company/plugins.git
/plugin marketplace add ./my-marketplace
/plugin marketplace add https://example.com/marketplace.json
```

安装 plugin：

```text
/plugin install plugin-name@marketplace-name
claude plugin install formatter@my-marketplace --scope project
```

### 4.2 Marketplace 使用是两步

官方文档把 marketplace 使用拆成两步：

```text
1. Add marketplace
   -> 注册 catalog
   -> 只让 Claude Code 能浏览
   -> 不安装具体插件

2. Install individual plugins
   -> 从 catalog 选择 plugin
   -> 按 scope 写 settings
   -> copy plugin 到本地 cache
```

这和 Codex 很接近：

```text
marketplace = 可发现源
plugin install = 具体能力进入本地运行资产
enable state = 当前 session 是否加载
```

### 4.3 安装 scope

Claude Code 插件安装 scope：

| Scope | Settings 文件 | 用途 |
| --- | --- | --- |
| `user` | `~/.claude/settings.json` | 个人全局可用，默认 |
| `project` | `.claude/settings.json` | 随项目共享，适合团队 |
| `local` | `.claude/settings.local.json` | 项目本地个人配置，通常 gitignored |
| `managed` | managed settings | 管理员安装，只读，用户不可修改 |

`enabledPlugins` 示例：

```json
{
  "enabledPlugins": {
    "formatter@acme-tools": true,
    "deployer@acme-tools": true,
    "analyzer@security-plugins": false
  }
}
```

`extraKnownMarketplaces` 示例：

```json
{
  "extraKnownMarketplaces": {
    "acme-tools": {
      "source": {
        "source": "github",
        "repo": "acme-corp/claude-plugins"
      }
    }
  }
}
```

对我们平台的映射：

```text
user scope     -> user-level plugin enable / preference
project scope  -> workspace/project plugin enable
local scope    -> dev/test sandbox config
managed scope  -> tenant/admin policy
```

### 4.4 缓存与文件解析

Claude Code 安装 plugin 时会复制 plugin 目录到本地 cache。官方 marketplace 文档明确：插件不能依赖 `../shared-utils` 之类 plugin 外部路径，因为安装时只复制 plugin 目录本身。

缓存设计带来几个约束：

```text
plugin root 是版本化、可替换、临时的 runtime artifact
plugin data 是持久化状态目录
插件更新后，新版本路径会变化
旧版本目录会保留一段时间再清理
```

官方变量：

```text
${CLAUDE_PLUGIN_ROOT}
  -> 当前安装版本的 plugin root
  -> 更新后会变化
  -> 不应写入持久状态

${CLAUDE_PLUGIN_DATA}
  -> ~/.claude/plugins/data/{id}/
  -> 跨版本持久
  -> 适合 node_modules、venv、cache、generated files、state

${CLAUDE_PROJECT_DIR}
  -> 项目 root
```

重要行为：

```text
Plugin 更新发生在 session 中途:
  -> hook / monitor / MCP / LSP 继续使用旧版本路径
  -> /reload-plugins 后 hooks / MCP / LSP 切换到新路径
  -> monitors 需要重启 session
```

这说明 Claude Code 把 plugin artifact 和 runtime process 生命周期做了弱绑定：更新不会强行杀掉已运行能力。

## 5. Plugin Manifest

### 5.1 manifest 主要字段

`.claude-plugin/plugin.json` 支持：

```json
{
  "name": "plugin-name",
  "displayName": "Plugin Name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["deployment", "ci-cd"],
  "skills": "./custom/skills/",
  "commands": "./commands/",
  "agents": "./agents/",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json",
  "lspServers": "./.lsp.json",
  "userConfig": {},
  "channels": [],
  "dependencies": []
}
```

组件字段：

| 字段 | 作用 |
| --- | --- |
| `skills` | skill 目录，包含 `<name>/SKILL.md` |
| `commands` | flat markdown command 或 command 目录 |
| `agents` | subagent markdown 文件 |
| `hooks` | hook config path 或 inline config |
| `mcpServers` | MCP config path 或 inline config |
| `lspServers` | LSP config path 或 inline config |
| `experimental.monitors` | background monitor config |
| `experimental.themes` | theme files |
| `userConfig` | 启用时让用户填写配置 |
| `channels` | 外部消息注入通道声明 |
| `dependencies` | 依赖其他 plugins |

### 5.2 userConfig 与敏感信息

`userConfig` 用来声明启用插件时需要用户填写的配置，避免手工改 settings。

示例：

```json
{
  "userConfig": {
    "api_endpoint": {
      "type": "string",
      "title": "API endpoint",
      "description": "Your team's API endpoint"
    },
    "api_token": {
      "type": "string",
      "title": "API token",
      "description": "API authentication token",
      "sensitive": true
    }
  }
}
```

关键点：

- `sensitive: true` 会 mask input。
- 敏感值进入 secure storage，而不是普通 `settings.json`。
- `${user_config.*}` 可用于 MCP、LSP、monitor command 变量替换。

对我们平台的映射：

```text
userConfig schema
  -> plugin config form
  -> non-sensitive config table
  -> sensitive config goes Credential Broker / secret manager
```

## 6. Session / Reload 时的动态加载

Claude Code 支持：

```text
/plugin install
/plugin enable
/plugin disable
/plugin uninstall
/reload-plugins
```

官方文档说明：安装、启用或禁用 plugin 后，运行 `/reload-plugins` 可不重启 session 即加载变更。`/reload-plugins` 会重新加载 active plugins，并显示：

```text
plugins count
skills count
agents count
hooks count
plugin MCP servers count
plugin LSP servers count
```

运行时推导：

```text
Claude Code session start / reload-plugins
  -> 读取 user/project/local/managed settings
  -> 合并 enabledPlugins
  -> 解析 known marketplaces / cache
  -> 对每个 enabled plugin 定位 cache root
  -> 读取 .claude-plugin/plugin.json 或默认目录
  -> 发现 skills / commands / agents / hooks / MCP / LSP / monitors / themes
  -> 做 namespace 与权限配置
  -> 更新当前 session capability registry
```

注意：插件变更不是立即无条件进入 running session，通常需要 `/reload-plugins` 或新 session。

## 7. Skill 动态加载链路

### 7.1 skill 的上下文加载策略

Claude Code 文档明确：

```text
默认:
  -> skill name + description 在 session/request 中可见
  -> full SKILL.md 只在 skill 被调用时加载

disable-model-invocation: true:
  -> skill 对 Claude 不可见
  -> 描述不进入上下文
  -> 只有用户显式 /skill-name 调用时才加载

user-invocable: false:
  -> 用户菜单隐藏
  -> Claude 仍可自动调用
```

这个策略是 Claude Code 避免 token 膨胀的核心。

对比表：

| Frontmatter | 用户可调用 | Claude 可自动调用 | 上下文加载 |
| --- | --- | --- | --- |
| 默认 | 是 | 是 | 描述常驻，全文按需 |
| `disable-model-invocation: true` | 是 | 否 | 不进上下文，用户调用时全文加载 |
| `user-invocable: false` | 否 | 是 | 描述常驻，全文按需 |

### 7.2 plugin skill 命名空间

plugin skill：

```text
plugin-name/skills/hello/SKILL.md
  -> /plugin-name:hello
```

命名规则：

```text
plugin manifest name = namespace prefix
skill folder name = skill name
```

为什么重要：

- 避免多个 plugin 都有 `/deploy`、`/commit`、`/review` 的冲突。
- 让 Claude 和用户明确能力来源。
- 让插件禁用时，相关 namespace 能整体移除。

### 7.3 skill 运行链路

用户显式调用：

```text
用户输入 /plugin-name:skill-name ARGUMENTS
  -> Claude Code 解析 slash command / skill
  -> 定位 plugin cache root + skill path
  -> 读取 SKILL.md
  -> 替换 $ARGUMENTS 或命名 arguments
  -> 将 skill content 注入当前会话
  -> Claude 按 skill 指令执行
```

Claude 自动调用：

```text
用户自然语言任务
  -> Claude 看到 skill names/descriptions
  -> 判断某个 skill relevant
  -> 通过 Skill tool 加载 full SKILL.md
  -> 执行 skill 工作流
```

### 7.4 skill 权限控制

Claude Code 允许通过权限规则限制 Skill tool：

```text
Skill
Skill(commit)
Skill(review-pr *)
Skill(deploy *)
```

skill 自身也可以定义 `allowed-tools`。当 skill active 时，允许 Claude 使用这些工具而不逐次审批，但全局权限仍然是基线。

对我们平台的映射：

```text
Skill summary index
  -> description-level capability discovery
  -> full skill context on invocation
  -> per-skill allowed tool set
  -> side-effect skill must user-only
```

## 8. MCP 动态加载与执行链路

### 8.1 plugin MCP 配置

plugin 可以提供 `.mcp.json` 或 manifest inline `mcpServers`：

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    },
    "plugin-api-client": {
      "command": "npx",
      "args": ["@company/mcp-server", "--plugin-mode"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

官方行为：

```text
plugin MCP servers start automatically when plugin is enabled
servers appear as standard MCP tools in Claude toolkit
plugin servers can be configured independently of user MCP servers
```

### 8.2 MCP 上下文加载

Claude Code feature overview 明确说明：

```text
MCP servers:
  When: session start
  What loads: connected server tool names
  Full JSON schemas stay deferred until Claude needs a specific tool
  Context cost: tool search is on by default, idle MCP tools consume minimal context
```

这说明 Claude Code 的 MCP 工具暴露更接近：

```text
初始上下文:
  -> server/tool names
  -> lightweight descriptors

需要调用具体 tool:
  -> tool search / deferred schema
  -> 加载具体 JSON schema
  -> 执行 MCP tool
```

这和 Codex 的 deferred MCP + tool_search 模型非常一致。

### 8.3 MCP 调用链路

运行时推导：

```text
session / reload
  -> 发现 enabled plugin 的 MCP config
  -> 替换 ${CLAUDE_PLUGIN_ROOT} / ${CLAUDE_PLUGIN_DATA} / ${user_config.*}
  -> 启动 stdio MCP server 或连接 MCP endpoint
  -> 获取 tool/resource 列表
  -> tool names 进入 Claude 可见工具集合
```

调用时：

```text
Claude 选择 MCP tool
  -> 如 schema 未加载，先通过 tool search / deferred mechanism 加载
  -> PreToolUse hooks 触发
  -> permission / approval 检查
  -> MCP client 调用 server tool
  -> PostToolUse / PostToolUseFailure hooks 触发
  -> tool result 回到 Claude
```

### 8.4 MCP 故障与 reload

官方提示：MCP 连接可能在 session 中 silently fail，server 断开后工具会消失。如果 Claude 试图调用已消失工具，需要 `/mcp` 检查连接。

对我们平台的启发：

```text
Runtime health 必须参与 capability visibility
tool schema cache 必须跟 runtime state 绑定
MCP server disconnect 后不能继续暴露工具
```

## 9. Hook 动态链路

### 9.1 hook 是外部生命周期执行器

Claude Code hooks 可以响应 session、prompt、tool、permission、subagent、task、file、worktree、compaction、MCP elicitation 等事件。

常见事件：

```text
SessionStart
Setup
UserPromptSubmit
UserPromptExpansion
PreToolUse
PermissionRequest
PermissionDenied
PostToolUse
PostToolUseFailure
PostToolBatch
Notification
SubagentStart
SubagentStop
TaskCreated
TaskCompleted
Stop
StopFailure
InstructionsLoaded
ConfigChange
CwdChanged
FileChanged
WorktreeCreate
WorktreeRemove
PreCompact
PostCompact
Elicitation
ElicitationResult
SessionEnd
```

### 9.2 hook 类型

Claude Code 支持多类 hook handler：

| 类型 | 行为 |
| --- | --- |
| `command` | 启动本地命令，事件 JSON 通过 stdin 传入 |
| `http` | POST 事件 JSON 到 URL |
| `mcp_tool` | 调用已连接 MCP server 的 tool |
| `prompt` | 把 hook input 和 prompt 发给 Claude model，返回结构化决策 |
| `agent` | 启动 subagent 做验证，最多多轮检查后返回决策 |

部分事件和模式对 hook 类型有限制。比如 `SessionStart` 主要支持 command 和 mcp_tool。

### 9.3 PreToolUse 示例链路

官方文档用阻止 `rm -rf` 的 `PreToolUse` hook 举例。完整链路：

```text
Claude 准备执行 Bash("rm -rf /tmp/build")
  -> PreToolUse event fires
  -> matcher = "Bash" 命中
  -> if condition 继续筛选 Bash(rm *)
  -> hook command 启动
  -> Claude Code 将事件 JSON 写入 stdin:
       { "tool_name": "Bash", "tool_input": { "command": "rm -rf /tmp/build" }, ... }
  -> hook 输出 JSON:
       permissionDecision = "deny"
  -> Claude Code 阻止 tool call
  -> 把阻止原因反馈给 Claude
```

### 9.4 hook 并发与决策

官方行为：

```text
所有匹配 hooks 并行运行
相同 handler 自动 deduplicate
command hook 按 command + args 去重
HTTP hook 按 URL 去重
```

退出码：

```text
exit 0:
  -> 成功
  -> stdout 如是 JSON，按事件语义解析

exit 2:
  -> blocking error
  -> stderr 反馈给 Claude
  -> 对 PreToolUse / UserPromptSubmit 等会阻止动作

其他非零:
  -> 多数事件视为 non-blocking error
  -> 继续执行
```

### 9.5 hook 与上下文成本

Hooks 默认不加载任何内容进模型上下文，因为它们在外部执行。只有以下情况会增加上下文：

```text
SessionStart / UserPromptSubmit / UserPromptExpansion stdout 添加上下文
hook JSON 返回 additionalContext
PostToolUse 替换或追加 tool feedback
async hook 完成后在下一轮交付 context
```

这是一种非常适合企业平台借鉴的模式：

```text
Policy / Audit / Validation 尽量在模型外执行
只有决策结果或必要反馈进入模型上下文
```

### 9.6 defer tool call

Claude Code hooks 支持 `permissionDecision: "defer"`，用于非交互 `claude -p` 集成场景。

流程：

```text
Claude 调用 AskUserQuestion
  -> PreToolUse fires
  -> hook 返回 permissionDecision = "defer"
  -> tool 不执行
  -> process 退出 stop_reason = "tool_deferred"
  -> 调用方读取 deferred_tool_use
  -> 外部 UI 收集答案
  -> claude -p --resume <session-id>
  -> 同一个 tool call 再次触发 PreToolUse
  -> hook 返回 allow + updatedInput
  -> tool 执行，Claude 继续
```

对我们平台的启发：

```text
human-in-the-loop 不一定要阻塞 Agent 进程
可以持久化 pending tool call
外部系统收集输入后 resume
```

## 10. Subagent 动态链路

### 10.1 subagent 作为上下文隔离机制

Claude Code subagent 是专用 AI assistant：

```text
独立 purpose / description
独立 context window
独立 system prompt
可配置 tool allowlist / denylist
可选 model / effort / maxTurns
```

Claude 遇到匹配任务时，可以自动 delegate；用户也可以手动调用。

### 10.2 plugin-shipped agents

plugin 可在 `agents/` 目录提供 subagent：

```markdown
---
name: security-reviewer
description: Review code for vulnerabilities and risky patterns
model: sonnet
effort: medium
maxTurns: 20
disallowedTools: Write, Edit
---

Detailed system prompt...
```

plugin agents 支持：

```text
name
description
model
effort
maxTurns
tools
disallowedTools
skills
memory
background
isolation
```

安全限制：

```text
plugin-shipped agents 不支持:
  hooks
  mcpServers
  permissionMode

isolation 目前只支持 "worktree"
```

这个限制很关键：插件可以提供 agent prompt 和 tool 策略，但不能通过 agent 自带 MCP/hook/permissionMode 绕过主会话治理。

### 10.3 subagent 运行时加载

feature overview 说明：

```text
When: on demand
What loads:
  -> agent 自己的 system prompt
  -> skills 字段列出的 skill 全文
  -> CLAUDE.md 和 git status，Explore/Plan 除外
  -> lead agent 传入的任务上下文
Context cost:
  -> 与主 session 隔离
  -> 不继承主会话历史或已调用 skills
```

subagent 中 skills 的加载和主 session 不同：

```text
主 session:
  -> skill 描述常驻，全文按需

subagent:
  -> agents frontmatter 中 skills 字段列出的 skills 在启动时全文预加载
  -> subagent 仍可通过 Skill tool 发现/调用未列出的 project/user/plugin skills
```

### 10.4 subagent 调用链路

运行时推导：

```text
主 Claude 判断任务适合某 agent
  -> 根据 agent description 选择 agent
  -> 创建 isolated context
  -> 注入 agent system prompt
  -> 注入 selected tools / disallowedTools
  -> 注入 agent.skills 全文
  -> 可选创建 worktree isolation
  -> subagent 独立执行
  -> SubagentStart / SubagentStop hooks 触发
  -> 结果汇总返回主会话
```

对我们平台的启发：

```text
Subagent 是 token 控制和复杂任务隔离手段
但它是强 runtime 能力
MVP 不宜作为普通 plugin 开放
更适合二期 Agent Template / Team Agent
```

## 11. LSP 动态链路

### 11.1 LSP plugin 的角色

Claude Code plugin 可以提供 `.lsp.json` 或 manifest inline `lspServers`。

LSP 让 Claude 获得代码智能：

```text
实时 diagnostics
go to definition
find references
hover info
type information
code symbol docs
```

示例：

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

注意：LSP plugin 通常不包含 language server binary，只配置 Claude Code 如何连接。用户仍需安装 `gopls`、`pyright-langserver`、`rust-analyzer` 等。

### 11.2 LSP 运行时链路

运行时推导：

```text
plugin enabled / reload
  -> 发现 .lsp.json / lspServers
  -> 校验 command 是否在 PATH
  -> 按文件扩展映射 language
  -> 启动 LSP server
  -> 文件编辑后 LSP 产生 diagnostics
  -> Claude 看到 error / warning / code intelligence
```

LSP 不应该被理解成 prompt 插件。它更像 runtime side channel，按文件变化产生结构化 code intelligence。

对我们平台的映射：

```text
Code Intelligence Plugin
  -> Runtime Host / IDE sidecar
  -> diagnostics event
  -> symbol lookup tool
  -> not MVP generic business plugin
```

## 12. Monitor 动态链路

### 12.1 Monitor 是后台事件源

plugin 可配置 background monitors。官方说明：

```text
when = "always"
  -> session start 和 plugin reload 时启动

when = "on-skill-invoke:<skill-name>"
  -> 该 plugin 的指定 skill 首次 dispatch 时启动
```

monitor command 支持变量：

```text
${CLAUDE_PLUGIN_ROOT}
${CLAUDE_PLUGIN_DATA}
${CLAUDE_PROJECT_DIR}
${user_config.*}
${ENV_VAR}
```

### 12.2 monitor 生命周期

官方行为：

```text
disable plugin mid-session 不会停止已运行 monitor
monitor 在 session 结束时停止
plugin 更新 mid-session 后 monitor 继续旧版本路径
monitor 需要重启 session 才切换新版本
```

运行时推导：

```text
session start / reload
  -> 发现 enabled plugin monitors
  -> 判断 when
  -> 启动 background command
  -> stdout / event 作为 notification 注入 Claude Code
  -> session end 清理 process
```

对我们平台的启发：

```text
Monitor = Trigger / Event Source / Worker
需要生命周期、资源、日志、重启、权限、审计
不应进入 MVP 的普通 tool runtime
```

## 13. Channel 动态链路

Claude Code plugin manifest 支持 `channels`，用于 Telegram、Slack、Discord 风格的消息注入。

虽然这部分官方页面只在 manifest 字段中简要提到，但从能力边界看，它接近：

```text
外部消息源
  -> channel declaration
  -> MCP server 或 connector 接收消息
  -> 注入 Claude Code session
```

对我们平台来说，channel 不应和普通 tool 混为一谈，更接近：

```text
Event Source Plugin
Trigger Plugin
External Conversation Connector
```

## 14. Token 与上下文控制机制

Claude Code 的上下文控制非常值得借鉴。

### 14.1 不同功能加载时机

官方 feature overview 给出清晰分层：

| 功能 | 加载时机 | 进入上下文内容 | 成本 |
| --- | --- | --- | --- |
| `CLAUDE.md` | session start | 全文 | 高，常驻 |
| Skills | 描述 session/request 可见，全文按需 | name + description，调用时全文 | 低到中 |
| User-only skills | 用户显式调用前不加载 | 无 | 零直到调用 |
| MCP | session start 连接 | tool names，schema deferred | 低 |
| Subagents | on demand | 独立上下文 | 不污染主 session |
| Hooks | on trigger | 默认无，除非返回 context | 接近零 |

### 14.2 Skill token 控制

策略：

```text
用 description 做选择，不放全文
side-effect skills 加 disable-model-invocation
user-only skill 不进 Claude context
skillOverrides 可把第三方 skill 改成 name-only / user-invocable-only / off
```

注意：官方说明 plugin skills 不受 `skillOverrides` 影响，需要通过 `/plugin` 管理。

### 14.3 MCP token 控制

策略：

```text
session start 只加载 tool names
full JSON schemas deferred until specific tool is needed
tool search 默认启用
/mcp 可查看每个 server token cost
不用的 server 应断开
```

### 14.4 Subagent token 控制

策略：

```text
独立 context window
不继承主 conversation history
不继承主 session invoked skills
只把 lead agent 传入的任务上下文给 subagent
```

这适合长任务和搜索型任务，避免主上下文膨胀。

### 14.5 Hook token 控制

策略：

```text
hook 外部执行
默认不进模型上下文
只返回决策/少量 additionalContext
async hook 结果下一轮再注入
```

## 15. 一次 Claude Code Plugin Turn 的完整推导链路

下面把一次插件能力使用串起来。

### 15.1 session start

```text
claude 启动
  -> 读取 settings 层:
       managed
       user ~/.claude/settings.json
       project .claude/settings.json
       local .claude/settings.local.json
  -> 读取 enabledPlugins
  -> 读取 extraKnownMarketplaces
  -> 读取 plugin cache
  -> 解析 enabled plugin
  -> 发现 skills / agents / hooks / MCP / LSP / monitors
  -> 启动 plugin MCP servers
  -> 启动 LSP servers
  -> 按 when 启动 monitors
  -> skill descriptions 进入上下文索引
  -> MCP tool names 进入工具索引，schema deferred
```

### 15.2 用户请求

```text
用户输入自然语言或 /plugin-name:skill
  -> Claude 根据 task 和 skill descriptions 选择是否调用 skill
  -> 若显式 /plugin-name:skill:
       直接加载该 skill 全文
  -> 若需要 MCP:
       通过 tool names / tool search 定位具体 tool
       deferred 加载 tool schema
  -> 若适合 subagent:
       按 agent description 创建 isolated subagent
  -> 若触发 hook event:
       外部执行 hook
```

### 15.3 skill 执行

```text
Skill invoked
  -> 读取 SKILL.md
  -> 替换 $ARGUMENTS / named arguments
  -> 注入当前 conversation 或 subagent context
  -> Claude 按 workflow 执行
  -> workflow 可引导 Claude 调 MCP / Bash / Read / Edit 等 tools
```

### 15.4 MCP tool 执行

```text
Claude 选择 MCP tool
  -> deferred schema 如未加载，先加载
  -> PreToolUse hooks
  -> permission check / approval
  -> MCP client 调用 plugin MCP server
  -> PostToolUse / PostToolUseFailure hooks
  -> result 回到 Claude
```

### 15.5 subagent 执行

```text
Claude 选择 agent
  -> SubagentStart hook
  -> 创建 isolated context
  -> 加载 agent prompt / tools / skills / memory / isolation
  -> subagent 执行多轮任务
  -> SubagentStop hook
  -> summary/result 返回主 Claude
```

### 15.6 hook 介入

```text
任意 lifecycle event
  -> event fires
  -> matcher / if condition
  -> command/http/mcp_tool/prompt/agent hook
  -> 输出 allow / deny / block / defer / additionalContext / continue
  -> Claude Code 按事件语义继续或阻断
```

## 16. 与 Codex 的关键差异

| 维度 | Claude Code | Codex |
| --- | --- | --- |
| 插件目录 | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| 插件能力 | skills、commands、agents、hooks、MCP、LSP、monitors、themes、channels | skills、apps、MCP、hooks、assets |
| marketplace | official + Git/local/URL + seed + managed restrictions | official/local/repo/Git/remote catalog |
| enable state | `enabledPlugins` in settings scopes | `~/.codex/config.toml` plugins table |
| skill 调用 | `/plugin:skill`，Skill tool，description 常驻 | `$skill` / skill input item，progressive disclosure |
| MCP schema | tool names at start，schema deferred，tool search on by default | direct if small，deferred/tool_search if large |
| subagent | 一等能力，plugin 可打包 agents | Codex 支持 subagents，但 plugin 能力更收敛 |
| hooks | 事件更多，支持 command/http/mcp_tool/prompt/agent/async/defer | 当前文档中 command 为主，plugin hooks opt-in |
| LSP/monitor | plugin 一等组件 | Codex plugin 当前公开能力较少涉及 |
| runtime 边界 | 本地 CLI runtime 执行 | 本地 Codex runtime / app-server |

## 17. 对我们企业 Plugin 平台的设计建议

### 17.1 能力包模型要比 Codex 更接近 Claude Code

Claude Code 证明 plugin 不是单一 tool 协议。我们的 manifest 应预留：

```yaml
capabilities:
  skills: []
  tools: []
  mcp_servers: []
  openapi: []
  data_sources: []
  hooks: []
  agents: []
  monitors: []
  lsp: []
  channels: []
  ui: []
```

但 MVP 不需要全实现。

### 17.2 MVP 和后续能力分层

MVP：

```text
Skill Context API
OpenAPI / REST connector
HTTP MCP
stdio MCP via Runtime Host
Credential Broker
Policy Engine
Capability Resolver
Tool Invocation Gateway
Audit / Observability
```

二期：

```text
Hook Plugin
Trigger / Monitor Plugin
Data Source pipeline
Agent Template / Subagent Plugin
Runtime Host worker
Plugin marketplace review / signing
```

三期：

```text
LSP / Code Intelligence
Channel / Message Injection
Workflow Plugin
Plugin dependency resolver
Plugin auto-update channels
```

### 17.3 token 控制必须照着 Claude Code 设计

建议策略：

```text
Plugin:
  -> 只注入 plugin summary

Skill:
  -> 初始只注入 name/description
  -> side-effect skill 默认 user-only
  -> full skill on invocation

MCP / Tool:
  -> 初始只注入 namespace/tool summary
  -> schema deferred
  -> capability_search 加载 selected schema

Hook:
  -> 外部执行
  -> 只注入 decision / short feedback

Subagent:
  -> 独立上下文
  -> 不污染主会话
```

### 17.4 安全治理不能照搬本地 trust 模型

Claude Code 是本地开发者工具，所以很多能力直接在用户机器上执行：

```text
hook command
monitor command
MCP server command
LSP command
plugin scripts
```

企业平台不能让业务 Agent 主进程直接运行这些能力。应改造成：

```text
Runtime Host / worker / container
  -> resource limit
  -> network policy
  -> filesystem policy
  -> timeout
  -> secret injection
  -> audit logs
  -> process lifecycle
```

### 17.5 `CLAUDE_PLUGIN_DATA` 模型值得采用

我们也应区分：

```text
plugin artifact root:
  -> 只读
  -> 版本化
  -> 可替换
  -> 不存持久状态

plugin data root:
  -> 持久
  -> 跨版本
  -> 存 dependency cache / generated files / local state
  -> 受 quota 管理
```

对应平台模型：

```text
/plugins/artifacts/<plugin>/<version>/
/plugins/data/<tenant>/<workspace>/<plugin>/
```

### 17.6 `/reload-plugins` 对应我们的 capability refresh

Claude Code 的 `/reload-plugins` 对应企业平台：

```text
PluginChanged event
  -> rebuild Capability Index
  -> refresh Runtime Host mounts/processes
  -> refresh MCP server registry
  -> refresh Skill index
  -> refresh Agent tool cache
  -> emit audit event
```

不要等到业务 Agent 调用时才同步 marketplace 或重建索引。

## 18. 风险判断

| 能力 | 风险 | 建议 |
| --- | --- | --- |
| hooks | 任意命令执行、可阻断/修改工具调用 | MVP 做平台内部事件，不开放脚本 |
| monitors | 长驻进程、资源泄漏、事件注入 | 二期 Runtime Host worker |
| plugin MCP stdio | 本地进程、依赖冲突、凭据注入 | Runtime Host 托管 |
| agents | 权限继承、成本、递归协作 | 二期 Agent Template，权限默认收窄 |
| LSP | 长驻进程、语言 server 安装复杂 | 独立 code intelligence 模块 |
| channels | 外部事件注入、身份鉴别、回放 | Trigger/Event Source 体系 |
| userConfig sensitive | 凭据泄漏 | Credential Broker / secret manager |

## 19. 参考资料

- Claude Code Plugins Reference: https://code.claude.com/docs/en/plugins-reference
- Claude Code Create Plugins: https://code.claude.com/docs/en/plugins
- Claude Code Discover Plugins: https://code.claude.com/docs/en/discover-plugins
- Claude Code Plugin Marketplaces: https://code.claude.com/docs/en/plugin-marketplaces
- Claude Code Skills: https://code.claude.com/docs/en/skills
- Claude Code Feature Overview: https://code.claude.com/docs/en/features-overview
- Claude Code Hooks: https://code.claude.com/docs/en/hooks
- Claude Code Subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code Settings: https://code.claude.com/docs/en/settings
