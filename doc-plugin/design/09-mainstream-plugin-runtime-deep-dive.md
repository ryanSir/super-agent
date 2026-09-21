# 09. 主流 Agent 插件体系与运行时调用链路深度分析

## 1. 结论先行

本轮调研重点不再停留在“插件是什么”，而是拆解主流 Agent 产品和开源框架在插件管理、能力发现、运行时执行、权限凭据、上下文注入和 token 控制上的完整链路。

核心结论如下：

1. **主流框架已经不把插件等同于单个 Tool。** Codex、Claude Code、Dify 都把插件理解成“能力包”：可以包含 skills、tools、MCP、API connector、hooks、subagents、data source、model provider、trigger 或 UI 元数据。
2. **插件管理面和运行时调用面必须分离。** Dify 通过 `dify-plugin-daemon` 把插件安装、runtime、debug、serverless 调用从主 API 进程中拆出去；Codex 和 Claude Code虽然是本地客户端模型，也把 marketplace、cache、enable state、MCP server、hook、skill discovery 做成独立配置链路。
3. **Agent 运行时不应该直接加载所有插件明细。** 先进做法是分层加载：先让模型看到 plugin / namespace / MCP server 的高层描述，再按任务加载相关 skill、tool schema 或资源。OpenAI API 的 `tool_search` 明确支持 deferred loading，用于避免一次性注入大量工具定义。
4. **需要执行代码的插件必须有运行隔离边界。** Open WebUI 明确区分 in-process Python、外部 HTTP / MCP、Pipeline worker；Dify 使用 daemon + local/debug/serverless runtime；Claude Code/Codex 本地执行 hooks、MCP、LSP、monitors 时依赖本地权限和 trust 机制。企业平台不能让业务 Agent 主进程直接承载插件代码。
5. **凭据不进模型上下文是共同底线。** Codex/Claude Code 把敏感配置放到 keychain 或本地 credentials；Dify 在 provider credential schema 和 runtime credentials 中注入；Open WebUI 要求 secret key 和管理员配置。我们的平台应由 Credential Broker 在调用时注入，模型只看到能力描述和参数 schema。

对我们当前 Plugin 平台的判断：

```text
Plugin = 可安装、可授权、可治理、可运行、可观测的 Agent 能力包

管理面：
  SDK/CLI -> validate/package/sign/publish -> Registry/Marketplace
  -> install/enable/configure -> Capability Index

调用面：
  Agent -> Capability Resolver -> Policy Engine -> Credential Broker
  -> Tool Invocation Gateway -> Runtime 分流执行 -> Audit/Trace
```

这个方向和 Codex、Claude Code、Dify、Open WebUI 的演进方向一致；差异在于我们要把本地客户端和开源单体里的能力服务化、多租户化、可审计化。

## 2. 主流框架对比总览

| 框架/产品 | 插件定位 | 支持能力 | 管理方式 | 运行时方式 | 对我们的启发 |
| --- | --- | --- | --- | --- | --- |
| OpenAI Codex Plugins | 可共享的 Codex 能力包 | Skills、Apps/Connectors、MCP servers、Hooks、Assets | 官方/本地/repo marketplace，安装到本地 cache，config 中 enable/disable | Codex CLI/App 本地 session 加载，MCP/hook/app 由客户端和配置驱动 | 强参考 package layout、marketplace、cache、enable state、按需 skill/tool 使用 |
| Claude Code Plugins | 本地/项目/团队插件包 | Skills、Commands、Agents、Hooks、MCP、LSP、Monitors、Themes、Channels | marketplace + user/project/local/managed scope，插件 cache，CLI install/enable/disable | Claude Code 本地 runtime 启动 MCP/LSP/monitor，hooks 绑定生命周期事件 | 能力最完整，适合参考插件包边界、配置分层和生命周期事件 |
| Dify Plugins | Dify 应用平台扩展包 | Tool、Model Provider、Endpoint/Extension、Agent Strategy、Data Source、Trigger | CLI init/package，Marketplace 或上传 `.difypkg`，workspace 安装 | `dify-plugin-daemon` 托管 local/debug/serverless runtime，HTTP 调用转 runtime | 服务端插件平台最接近我们的企业目标，重点参考 daemon/runtime/签名/多租户 |
| Open WebUI | WebUI 扩展层 | Tools、Functions/Pipes/Filters/Actions、MCP、OpenAPI、Pipelines、Skills、Prompts | Admin / Workspace / Community import / External Tools | in-process Python、外部 HTTP/MCP、独立 Pipeline worker | 参考三层执行模型和安全边界：轻量内置、远程服务、重型 worker |
| OpenAI API / Agents SDK | 工具和能力接入协议层 | Function、MCP、File Search、Tool Search、Shell、Computer Use、Skills | 应用代码声明，或 runtime 动态发现 | Hosted tools、本地函数、remote MCP、client-executed tool search | 参考 `tool_search` 的动态工具加载，解决 token 爆炸 |

## 3. OpenAI Codex Plugins 调用链路

### 3.1 插件管理模型

Codex 的 plugin 是一个可分发目录，必需入口是：

```text
my-plugin/
  .codex-plugin/
    plugin.json
  skills/
  hooks/
  .mcp.json
  .app.json
  assets/
```

`plugin.json` 的职责是：

- 标识插件：`name`、`version`、`description`、`author`、`license`。
- 指向组件：`skills`、`mcpServers`、`apps`、`hooks`。
- 提供安装展示信息：`interface.displayName`、`shortDescription`、`defaultPrompt`、icon、logo、screenshots。

Codex 的 marketplace 是 JSON catalog，可以来自：

- 官方 Plugin Directory。
- repo 级 `$REPO_ROOT/.agents/plugins/marketplace.json`。
- personal 级 `~/.agents/plugins/marketplace.json`。
- 兼容旧目录的 `.claude-plugin/marketplace.json`。
- Git-backed marketplace 或 local marketplace root。

安装后，Codex 不直接使用 marketplace 源目录，而是复制到本地 cache：

```text
~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/
```

插件是否启用写入 `~/.codex/config.toml`，因此 install 和 enable 是两个状态：

```toml
[plugins."gmail@openai-curated"]
enabled = false
```

### 3.2 Codex 运行时发现链路

```text
Codex 启动或新 thread
  -> 读取用户级 config.toml
  -> 读取 repo marketplace / personal marketplace / official directory
  -> 解析 plugin state：available / installed / enabled
  -> 从 cache 加载 enabled plugin
  -> 解析 plugin.json
  -> 扫描 skills / .mcp.json / .app.json / hooks
  -> 生成当前 session 可见能力集合
```

Codex App Server API 中也能看到对应运行时接口：

- `plugin/list`：列出 marketplace 和 plugin state。
- `plugin/read`：读取 plugin 详情，包括 bundled skills、apps、MCP server names。
- `plugin/install` / `plugin/uninstall`：安装和卸载。
- `skills/list` / `skills/config/write`：列出、启用或禁用 skills。
- `mcpServerStatus/list`：列出 MCP servers、tools、resources、auth status。
- `mcpServer/tool/call`：调用 MCP tool。
- `thread/compact/start`：触发会话压缩。

这说明 Codex 不是简单把插件文件拼进 prompt，而是形成了 runtime state 和可查询能力接口。

### 3.3 Codex Agent 调用链路

Codex 的一次插件能力调用可以拆成四类。

**Skill 调用：**

```text
用户请求
  -> Codex 判断需要某个 installed skill
  -> 加载 skill frontmatter + SKILL.md 主体
  -> 必要时读取 skill references/scripts
  -> 注入当前模型上下文
  -> 模型按 skill 指令执行任务
```

Skill 是提示词/工作流能力，不是独立 runtime。它可能引用脚本或 MCP，但 skill 本身更像“任务方法说明”。

**App / Connector 调用：**

```text
用户请求
  -> Codex 选择 app connector
  -> 检查 app 是否安装/授权
  -> 按 app tool schema 发起调用
  -> connector 使用外部服务凭据
  -> 返回结构化结果
  -> 模型继续推理
```

**MCP 调用：**

```text
enabled plugin
  -> .mcp.json 定义 plugin-scoped MCP server
  -> Codex 启动/连接 MCP server
  -> 获取 server tools/resources
  -> 模型选择 MCP tool
  -> 按 tool approval policy 决定是否提示用户
  -> mcpServer/tool/call
  -> MCP result 回填模型上下文
```

Codex 允许对 plugin-scoped MCP server 做细粒度控制：

```toml
[plugins."my-plugin".mcp_servers.docs]
enabled = true
default_tools_approval_mode = "prompt"
enabled_tools = ["search"]

[plugins."my-plugin".mcp_servers.docs.tools.search]
approval_mode = "approve"
```

**Hook 调用：**

```text
session/tool/event 发生
  -> Codex 匹配 hooks event + matcher
  -> 检查 plugin_hooks feature、trust、权限
  -> 执行 command/http/mcp_tool/prompt/agent hook
  -> hook 输出影响事件后续处理或审计
```

Codex 当前对 plugin hooks 是显式开关：`[features].plugin_hooks = true`。

### 3.4 Codex 如何避免 token 爆炸

Codex 的策略不是单点，而是组合：

1. **Marketplace 和 cache 只进入本地状态，不进入模型上下文。** 模型不需要看到完整 plugin catalog。
2. **插件先以高层能力可见，组件按需加载。** skills、apps、MCP tools 只有在相关场景才进入上下文。
3. **MCP server 可按 server/tool allowlist 裁剪。** `enabled_tools` 和 per-tool approval 减少暴露面。
4. **skill 采用 progressive disclosure。** 先加载 `SKILL.md`，引用文件、脚本、资源按需读取。
5. **会话压缩独立存在。** `/compact` 和 `thread/compact/start` 用于长任务保留关键状态。
6. **工具搜索是更系统的方向。** OpenAI API 的 `tool_search` 支持 deferred loading，只让模型先看到 namespace/MCP server 高层描述，真正需要时再加载具体工具定义。

对我们的映射：

```text
Codex plugin cache        -> Registry package cache / installed artifact
Codex config enabled      -> workspace/agent/user enable state
Codex skills/list         -> Skill Context API
Codex mcpServerStatus     -> Capability Resolver + MCP Runtime status
Codex mcpServer/tool/call -> Tool Invocation Gateway
Codex tool_search 思路    -> Capability Search / Deferred Tool Schema Loading
```

## 4. Claude Code Plugins 调用链路

### 4.1 插件能力范围

Claude Code 的插件能力比 Codex 更宽，插件可以包含：

- `skills/` 或 `commands/`：任务工作流和 slash command。
- `agents/`：专用 subagent。
- `hooks/hooks.json`：生命周期事件处理。
- `.mcp.json`：MCP server。
- `.lsp.json`：语言服务。
- `monitors/monitors.json`：后台监控进程。
- `themes/`：主题。
- `channels`：通过 MCP server 注入外部消息通道。
- `userConfig`：启用时向用户收集配置，敏感值进安全存储。

Claude Code 的 manifest 是 `.claude-plugin/plugin.json`。官方文档明确：如果没有 manifest，Claude Code 也会按默认目录自动发现组件，并用目录名推导 plugin name。

### 4.2 安装和配置分层

Claude Code 插件安装有四个 scope：

| Scope | 配置文件 | 含义 |
| --- | --- | --- |
| user | `~/.claude/settings.json` | 个人全局可用 |
| project | `.claude/settings.json` | 项目共享，可进版本控制 |
| local | `.claude/settings.local.json` | 项目本地，通常 gitignored |
| managed | managed settings | 企业托管，只读或受管控 |

这个设计对我们很重要，因为企业平台也需要类似分层：

```text
managed scope  -> tenant / enterprise policy
project scope  -> workspace / project enable
user scope     -> user preference / user auth
local scope    -> dev/test sandbox config
```

### 4.3 Claude Code 运行时发现链路

```text
Claude Code 启动 / session resume
  -> 解析 user/project/local/managed settings
  -> 发现已安装插件和启用状态
  -> 从插件 cache 解析 plugin.json 或默认目录
  -> 加载 skills/commands/agents/hooks/mcp/lsp/monitors
  -> 做命名空间处理：plugin-name:component-name
  -> 准备当前 session 的可用能力
```

Claude Code Agent SDK 也支持直接加载本地插件：

```typescript
plugins: [
  { type: "local", path: "./my-plugin" },
  { type: "local", path: "/absolute/path/to/another-plugin" }
]
```

SDK 初始化消息会返回 loaded plugins 和 slash commands，说明插件发现结果进入 session init state，而不是无结构地拼接。

### 4.4 Claude Code Agent 调用链路

**Skill / Command：**

```text
用户自然语言或 /plugin-name:skill-name
  -> Claude Code 根据描述或显式命令选中 skill
  -> 加载 SKILL.md 和必要资源
  -> 注入模型上下文
  -> 模型按 skill 完成任务
```

**Subagent：**

```text
主 Agent 判断需要专用 agent
  -> 根据 agents/*.md frontmatter 选择 agent
  -> 创建独立 agent session
  -> 注入 agent system prompt、tools、skills、memory、isolation
  -> subagent 独立执行
  -> 结果返回主 Agent
```

安全限制值得注意：插件自带 agents 不支持 `hooks`、`mcpServers`、`permissionMode`，避免插件通过 subagent 绕过主会话权限。

**Hook：**

Claude Code hooks 覆盖大量事件：

```text
SessionStart
UserPromptSubmit
PreToolUse / PostToolUse / PostToolUseFailure / PostToolBatch
PermissionRequest / PermissionDenied
SubagentStart / SubagentStop
PreCompact / PostCompact
InstructionsLoaded
ConfigChange
FileChanged
SessionEnd
...
```

Hook 类型包括：

- `command`：执行 shell 命令。
- `http`：向 URL POST 事件 JSON。
- `mcp_tool`：调用 MCP tool。
- `prompt`：让 LLM 评估上下文。
- `agent`：运行 agentic verifier。

这给我们的启发是：MVP 不一定开放任意 hook，但内部事件点应按这些生命周期预留。

**MCP / LSP / Monitor：**

```text
enabled plugin
  -> 解析 .mcp.json / .lsp.json / monitors.json
  -> 用 ${CLAUDE_PLUGIN_ROOT}、${CLAUDE_PLUGIN_DATA}、${user_config.*} 做变量替换
  -> 启动 MCP/LSP/monitor 子进程或连接服务
  -> 将 MCP tools、LSP diagnostics、monitor notifications 接入会话
```

Monitors 是长驻后台命令，stdout 行会作为 notification 送给 Claude。官方也明确 monitors 与 hooks 同 trust 级别，且中途禁用插件不停止已运行 monitor，session 结束才停止。这说明长驻执行能力必须谨慎治理。

### 4.5 Claude Code 如何避免 token 爆炸

Claude Code 的控制点包括：

1. **命名空间隔离。** plugin skills、commands、agents 用 `plugin-name:component-name` 避免冲突。
2. **只把 component index 和描述作为发现入口。** 具体 skill 或 agent prompt 在触发时加载。
3. **支持 `PreCompact` / `PostCompact` 生命周期。** 插件可参与压缩前后处理，但这也是治理风险点。
4. **userConfig 区分敏感和非敏感。** 敏感值不注入 skill/agent content，只进安全存储和子进程环境。
5. **LSP/monitor 不等于 prompt 注入。** 诊断、通知按事件进入，不把整个服务状态塞入 prompt。

对我们的映射：

```text
Claude scope model      -> tenant/workspace/agent/user scope
Claude hooks events     -> Platform lifecycle events + Policy/Audit
Claude agents           -> Agent Template / Team Agent 二期
Claude monitors         -> Trigger / Event Source / Runtime worker 二期
Claude userConfig       -> Plugin config schema + Credential Broker
Claude cache/local exec -> Runtime Host installed artifact + data dir
```

## 5. Dify Plugins 与 plugin-daemon 调用链路

### 5.1 插件能力范围

Dify 插件是服务端平台扩展，官方类型包括：

- Tool：给 Chatflow / Workflow / Agent 应用调用的外部能力。
- Model Provider：模型供应商插件。
- Extension / Endpoint：通过 HTTP webhook 或 endpoint 扩展服务。
- Agent Strategy：自定义 Agent 推理和工具调用策略，例如 Function Calling、ReAct、ToT、CoT。
- Data Source：知识管道的数据源，例如 web crawler、online document、online drive。
- Trigger：把第三方事件转换成 Dify workflow 可识别输入。

Dify 对我们最有参考价值，因为它已经把插件执行从主系统中拆出，形成 `dify-plugin-daemon`。

### 5.2 Dify 插件开发与发布链路

```text
dify plugin init
  -> 选择 plugin type：tool / agent-strategy / model / datasource / extension
  -> 生成 manifest.yaml、provider YAML、Python implementation、requirements.txt、assets
  -> 开发者实现 dify_plugin SDK 接口
  -> remote debug：python -m main 连接 debug daemon
  -> dify plugin package
  -> 生成 .difypkg
  -> Marketplace 发布或 direct upload
```

关键文件：

```text
manifest.yaml            # 插件 metadata、权限、资源限制、最低 Dify 版本
provider/*.yaml          # provider 信息、credentials schema、工具/数据源引用
tools/*.yaml             # tool name、description、parameters、llm_description
tools/*.py               # 具体 Tool._invoke 实现
main.py                  # plugin.run()
requirements.txt         # Python 依赖
_assets/                 # icon 等静态资源
```

Dify tool schema 有一个值得借鉴的设计：参数区分 `form` 和 `llm`。

- `llm`：由模型推断，进入工具 schema。
- `form`：由前端/配置预设，不必让模型每次决定。

这可以减少模型参数负担，也避免把不该由模型决定的配置暴露出去。

### 5.3 Dify 安装与验证链路

Dify plugin daemon 的生命周期包括 package、signature verification、install、upgrade、uninstall、reference counting 和 GC。

```text
上传 .difypkg 或 marketplace identifier
  -> daemon 解包 package
  -> 校验 manifest.yaml
  -> 签名验证：官方 key / 第三方 key / 强制拒绝未签名
  -> 保存 package 到 OSS：/packages/<author>/<plugin>/<version>-<checksum>.difypkg
  -> 写入 DB：Plugin、Installation、InstallTask
  -> 如果该版本已被其他 tenant 安装：走 DB-only fast path
  -> 如果第一次安装：准备 runtime、依赖、文件、serverless 部署
  -> 安装完成后 workspace 可启用
```

这个 fast path 很关键：插件二进制和依赖准备按版本复用，tenant 安装只是数据库授权关系，适合多租户平台。

### 5.4 Dify runtime 架构

`dify-plugin-daemon` 支持三类 runtime：

| Runtime | 工作方式 | 适用场景 |
| --- | --- | --- |
| Local runtime | daemon 启动插件子进程，通过 STDIN/STDOUT 通信 | 本机部署、私有化、开发和小规模生产 |
| Debug runtime | daemon 监听端口，等待开发者插件通过 TCP 连接 | 远程调试 |
| Serverless runtime | 插件打包到 AWS Lambda 等 serverless，通过 HTTP 调用 | 弹性执行、隔离部署 |

daemon 内部关键组件：

```text
HTTP server
  -> PluginManager
     -> packageBucket / installedBucket / mediaBucket
     -> ControlPanel
        -> runtime discovery
        -> watchdog
     -> SessionManager
        -> execution context
     -> io_tunnel
        -> SESSION_MESSAGE_TYPE_STREAM
        -> SESSION_MESSAGE_TYPE_INVOKE
        -> backwards invocation to Dify core
```

`io_tunnel` 是 Dify 的关键设计：插件执行不是简单 request/response，它支持流式数据和插件反向调用 Dify core。

### 5.5 Dify Agent 运行时调用链路

以 Tool Plugin 为例：

```text
用户请求进入 Dify Agent / Workflow
  -> Agent strategy / workflow node 决定调用某个 tool
  -> Dify API 查 workspace 已安装插件和 provider/tool metadata
  -> 根据 tool YAML 组装 LLM tool schema
  -> 模型生成 tool call
  -> Dify API 向 plugin-daemon 发起 HTTP invoke
  -> daemon 根据 tenant + plugin unique identifier 定位 runtime
  -> SessionManager 创建/复用执行 session
  -> Local runtime：写入插件子进程 stdin
  -> 插件 SDK 调用 Tool._invoke
  -> 插件使用 runtime.credentials 注入密钥
  -> 插件 yield ToolInvokeMessage
  -> daemon 通过 io_tunnel 流式返回
  -> Dify API 归一化结果
  -> Agent 继续模型调用或结束
```

以 Agent Strategy Plugin 为例：

```text
Dify Agent 应用启动
  -> 选择某个 Agent Strategy
  -> Dify 把模型、工具、query、history、参数传给 strategy plugin
  -> strategy plugin 自己实现 function calling / ReAct / CoT / ToT 循环
  -> 多轮：model invoke -> tool selection -> tool call -> result handling
  -> 达到结束条件或 max iteration
  -> 返回 Agent 最终输出
```

这类插件能力很强，但也最危险。它不仅提供工具，而是改变 Agent Runtime 的决策逻辑。我们 MVP 不建议开放 Agent Strategy Plugin，最多做内部可插拔策略。

以 Data Source Plugin 为例：

```text
知识管道启动
  -> Data Source Plugin 作为 pipeline start node
  -> provider 处理 OAuth/API key
  -> datasource core logic 分页拉取外部文档
  -> 标准化文档 metadata/content/blob/link
  -> 交给 Dify knowledge pipeline 做抽取、切分、索引
```

以 Trigger Plugin 为例：

```text
第三方 SaaS event
  -> webhook 到 Dify endpoint
  -> trigger provider 验签/分类 event
  -> event handler 转换成 Dify workflow input
  -> 启动 workflow
```

### 5.6 Dify 如何避免 token 爆炸

Dify 的 token 控制主要来自“schema 分层”和“runtime 外置”：

1. **provider metadata 和 tool metadata 分离。** LLM 只看到可调用 tool 的必要描述和 `llm_description`。
2. **参数分为 `llm` 和 `form`。** 预设参数不进入模型决策面。
3. **插件代码、依赖、manifest、README 不进上下文。** 它们只在 daemon 和 marketplace 管理面存在。
4. **Agent Strategy 才承担多轮循环。** 普通 Tool Plugin 不把复杂执行过程暴露给模型。
5. **Data Source 进入 RAG pipeline，而不是直接塞给 LLM。** 通过知识管道索引后检索，而不是每次全量注入。
6. **streaming result 可以边生成边消费。** 避免一次性构造超大工具结果。

对我们的映射：

```text
Dify plugin-daemon       -> Plugin Runtime Host
Dify manifest.yaml       -> plugin.yaml
Dify provider YAML       -> capability sub-manifest
Dify .difypkg            -> plugin package artifact
Dify signature verify    -> package signing / allowlist / review
Dify SessionManager      -> runtime session manager
Dify io_tunnel           -> runtime protocol + streaming + callback
Dify tenant installation -> workspace/agent install/enable relation
```

## 6. Open WebUI 扩展链路

### 6.1 三层扩展模型

Open WebUI 的扩展模型非常适合解释“不是所有插件都需要同一种 runtime”：

| 层 | 运行位置 | 适合场景 | 风险 |
| --- | --- | --- | --- |
| Tools & Functions | Open WebUI 主进程内 Python | 轻量工具、filters、pipes、actions | 与主服务共享 CPU/内存，安全风险高 |
| OpenAPI / MCP | 任意 HTTP endpoint | 外部服务、第三方 API、已有 MCP server | 需要运维外部 server |
| Pipelines | 独立 Docker / worker | GPU、大依赖、敏感/重型任务 | 需要额外基础设施 |

Open WebUI 明确警告：Tools、Functions、Pipelines 都是在服务器执行任意 Python 代码，必须只安装可信来源，并限制 Workspace/Admin 权限。

### 6.2 Open WebUI 能力发现和调用

**Tools：**

```text
管理员/用户安装 Tool
  -> Tool 作为 Workspace 能力保存
  -> Chat 时根据启用状态注入模型 tool schema
  -> 模型生成 tool call
  -> Open WebUI 主进程执行 Python tool
  -> 结果回填 conversation
```

**Functions：**

```text
管理员安装 Function
  -> Function 进入 Admin Panel
  -> Pipe：新增/代理模型 provider
  -> Filter：拦截输入或输出消息
  -> Action：扩展 UI 操作
  -> 在请求/响应生命周期中执行
```

**MCP：**

```text
Admin Settings -> External Tools
  -> Add Server
  -> Type = MCP (Streamable HTTP)
  -> 配置 Server URL 和 auth
  -> Open WebUI 连接 MCP server
  -> 暴露 MCP tools 给模型
  -> 模型调用 MCP tool
```

Open WebUI 当前原生 MCP 支持 Streamable HTTP。对于 stdio 或 SSE MCP server，官方建议用 `mcpo` 转换代理。

**OpenAPI：**

```text
Admin 添加 OpenAPI endpoint
  -> Open WebUI 读取 spec
  -> 自动发现 endpoints
  -> 暴露为模型可调用工具
```

Open WebUI 文档也指出，多数企业部署中 OpenAPI 仍更适合深度 SSO、API gateway、audit、quota、typed SDK、错误码和观测。

### 6.3 Open WebUI 如何避免 token 爆炸

1. **优先外部化服务。** OpenAPI/MCP/Pipeline 不把实现放进 prompt。
2. **Function Name Filter List。** MCP 可限制暴露给 LLM 的工具集合。
3. **系统工具按 feature toggle 注入。** Web Search、Knowledge、Memory、Notes、Calendar 等都受开关和权限控制。
4. **Native tool calling 优先。** 文档明确 legacy prompt-parsing 模式不再推荐，因为结构化 tool call 更 cache-friendly，也更稳定。
5. **重型数据通过 Knowledge/RAG 工具分页读取。** `view_file` / `view_knowledge_file` 支持 `offset`、`max_chars`，避免一次读取全量文档。

对我们的映射：

```text
Open WebUI in-process Tools  -> MVP 可不开放，或只内部受控
Open WebUI External Tools    -> OpenAPI/MCP Gateway
Open WebUI Pipelines         -> Plugin Runtime Host / worker
Open WebUI Function Filters  -> Policy / Guardrail / Middleware
Function Name Filter List    -> capability allowlist / exposed tool subset
```

## 7. Token 爆炸问题的系统性方案

插件平台最容易失败的点不是“怎么调用工具”，而是安装了几十个插件后，模型上下文被工具 schema、skill、说明文档、示例、权限文本淹没。主流方案可以总结为以下九层。

### 7.1 分层能力索引

不要让 Agent 一开始看到完整插件内容。

```text
Level 0: plugin id + display name + category
Level 1: capability summary / namespace description
Level 2: tool names + short descriptions
Level 3: selected tool schema
Level 4: selected skill full instructions
Level 5: supporting references/resources
Level 6: runtime result pages/chunks
```

模型默认只看 Level 1 或 Level 2。只有当它明确需要某个能力时，才加载 Level 3 以后。

### 7.2 Capability Resolver 先检索，后注入

```text
用户请求
  -> embedding / keyword / rules 检索候选 capability
  -> policy filter
  -> top-k capability summaries
  -> 模型选择
  -> 加载选中 capability schema
```

这相当于把 marketplace 和 Capability Index 当成检索库，而不是 prompt 附件。

### 7.3 Deferred Tool Schema Loading

参考 OpenAI `tool_search`：

```text
初始上下文：
  - namespace: "jira"
  - description: "Search, create and update Jira issues..."

模型需要具体操作：
  -> tool_search("jira issue search")
  -> 返回 search_issues / get_issue / list_projects schema
  -> 模型再调用 search_issues
```

最佳实践：

- namespace 或 MCP server 描述清晰但短。
- 每个 namespace 尽量少于 10 个高相关函数。
- 具体参数 schema 延迟加载。
- 已加载工具跨 turn 复用，避免重复注入。

### 7.4 Skill Progressive Disclosure

Skill 不应该把所有参考资料写进 `SKILL.md`。推荐：

```text
SKILL.md
  -> 只放触发条件、核心流程、约束、必要工具
references/
  -> 按需读取
scripts/
  -> 按需执行
assets/
  -> 按需引用
```

Agent 先读 skill 主体，再决定是否读取引用文件。

### 7.5 Tool Result Budget

工具结果必须有预算：

```text
max_result_tokens
max_items
max_chars_per_item
pagination: cursor / offset
summary_mode: none / brief / structured
attachments: link by id, not inline blob
```

Open WebUI 的 `view_file(offset, max_chars)` 和 Dify data source pipeline 都体现了这个原则。

### 7.6 权限裁剪先于模型选择

不要把用户无权使用的工具暴露给模型。

```text
all capabilities
  -> tenant policy
  -> workspace enable
  -> agent enable
  -> user permission
  -> credential available
  -> runtime health
  -> model-visible candidates
```

这既省 token，也避免模型计划一个无法执行的工具调用。

### 7.7 配置和凭据不进入上下文

以下内容不应该进入模型上下文：

- API key、OAuth token。
- webhook secret。
- 内部 endpoint secret。
- provider full config。
- 插件安装路径和本地文件系统布局。
- 不相关的 manifest metadata。

模型只需要知道“有一个可调用能力”和“参数怎么填”。凭据由 Credential Broker 在 runtime 注入。

### 7.8 长会话压缩

长任务需要压缩策略：

```text
conversation history
  -> 保留当前目标、已调用工具、关键结果、未完成事项
  -> 丢弃原始长日志、重复工具 schema、旧中间推理
  -> 工具结果落库，通过 result_id 引用
```

Codex 和 Claude Code 都有 compact 生命周期或命令。我们的平台可以在 Agent Runtime 或 Plugin Gateway 侧记录 `tool_result_id`，压缩后只保留摘要和引用。

### 7.9 观测 token 使用

每次工具注入和调用都应记录：

```text
agent_id
plugin_id
capability_id
schema_tokens
skill_tokens
result_tokens
input_tokens_before_call
output_tokens_after_call
latency
cache_hit
```

没有这些数据，很难判断 token 膨胀来自工具 schema、skill 文档还是工具结果。

## 8. 企业 Plugin 平台建议调用链路

### 8.1 插件准备链路

```text
Plugin Developer
  -> 编写 plugin.yaml / capabilities/*.yaml / skills/* / runtime/*
  -> plugin validate
     -> schema 校验
     -> 权限声明校验
     -> dependency 校验
     -> secret 字段校验
     -> token budget lint
  -> plugin package
     -> 生成 artifact
     -> 计算 checksum
     -> 签名
  -> plugin publish
     -> Registry 存储 package
     -> Marketplace 存储展示 metadata
     -> Security review / allowlist
  -> Admin install
     -> tenant/workspace 安装
     -> runtime artifact prepare
     -> credential config
  -> Agent enable
     -> agent 绑定 plugin/capability subset
     -> Capability Index 更新
```

### 8.2 Agent 运行时发现链路

```text
用户请求进入业务 Agent
  -> Agent Runtime 调用 Capability Resolver
     inputs:
       tenant_id
       workspace_id
       agent_id
       user_id
       query
       conversation_state
  -> Resolver 查询 Capability Index
  -> Policy Engine 过滤无权能力
  -> Credential Broker 标记 credential readiness
  -> Runtime Registry 标记 runtime health
  -> 返回 top-k capability summaries
  -> Agent 将候选能力摘要注入模型
```

注意：这里返回的是 summary，不是完整工具 schema。

### 8.3 Agent 运行时工具加载链路

```text
模型判断需要某类能力
  -> Agent Runtime 发起 capability_search / tool_search
  -> Capability Resolver 返回具体 tool schema 或 skill context
  -> Agent Runtime 注入 schema
  -> 模型生成 tool call
```

### 8.4 Agent 运行时执行链路

```text
模型生成 tool call
  -> Tool Invocation Gateway
     -> 参数 JSON schema 校验
     -> Policy Engine 二次检查
     -> Human approval 判断
     -> Credential Broker 注入凭据
     -> Rate limit / quota
     -> Audit start
  -> Runtime Router 分流
     -> Skill: 返回 context，不执行代码
     -> OpenAPI: HTTP 调用 remote API
     -> HTTP MCP: 调用 MCP endpoint
     -> stdio MCP: Runtime Host adapter
     -> Native Tool: Runtime Host worker/container
     -> Data Source: connector / pipeline
  -> Runtime 返回 structured result
  -> Result Normalizer
     -> 裁剪 / 分页 / 摘要 / 脱敏
  -> Audit end + Langfuse trace
  -> 模型继续推理
```

### 8.5 Runtime Host 设计边界

第一版建议 Runtime Host 只承载必须隔离执行的能力：

| 能力 | 是否进 Runtime Host | 原因 |
| --- | --- | --- |
| Skill | 否 | 上下文能力，不是执行型 runtime |
| OpenAPI | 否，优先 Gateway | HTTP 标准调用，核心是凭据和审计 |
| HTTP MCP | 否，优先 Gateway | 远程 MCP 自带服务边界 |
| stdio MCP | 是 | 需要进程管理、协议转换、健康检查 |
| Native Tool | 是 | 需要依赖隔离、超时、资源限制 |
| Hook | 二期，受控进入 | 任意脚本风险高 |
| Monitor / Trigger worker | 二期进入 | 长驻任务需要生命周期管理 |
| Agent Strategy | 暂不开放 | 会改变 Agent 核心决策边界 |

## 9. 我们和主流框架的取舍

| 设计问题 | Codex/Claude 做法 | Dify 做法 | 建议采用 |
| --- | --- | --- | --- |
| 插件是什么 | 本地可安装能力包 | 服务端平台插件包 | 能力包 + 治理单元 |
| marketplace | JSON catalog + cache | Marketplace / upload `.difypkg` | Registry + Marketplace + artifact cache |
| enable 粒度 | plugin / MCP server / tool | workspace 安装和使用 | tenant/workspace/agent/user + capability subset |
| runtime | 客户端本地执行 | daemon local/debug/serverless | 独立 Runtime Host |
| skills | 按需注入上下文 | Dify 无同等主能力 | Skill Context API |
| hooks | 生命周期脚本/HTTP/MCP/prompt/agent | 较少作为开放主能力 | 先做内部事件，二期开受控 hook |
| subagents | 插件可带 agents | Agent Strategy 插件 | MVP 不开放，二期 Agent Template |
| MCP | 插件可带 MCP config | Dify 主要自有 SDK/tool runtime | MCP Plugin + Gateway + stdio adapter |
| data source | app/connector 或 MCP | Data Source Plugin | Data Source Plugin + pipeline |
| token 控制 | skill 按需、tool config、compact、tool_search | schema 分层、runtime 外置、RAG pipeline | Capability Search + deferred schema + result budget |

## 10. 风险与落地优先级

### 10.1 不建议直接照搬

1. **不要照搬 Claude Code 任意 hook 脚本。** 企业平台中这会成为远程代码执行入口，必须走审批、签名、沙箱和审计。
2. **不要把 Agent Strategy Plugin 放进 MVP。** 它会改变 Agent 的规划、循环、工具选择和权限继承，边界比普通插件大很多。
3. **不要让业务 Agent 直接管理 MCP server。** 一旦各业务 Agent 自己接 MCP，平台会失去统一凭据、权限、审计和观测。
4. **不要把所有插件 tool schema 一次塞给模型。** 这是插件平台规模化后最直接的 token 成本问题。
5. **不要把 Runtime Host 做成 Plugin Core Service 内部模块。** POC 可以同仓同进程模拟，生产建议独立边界。

### 10.2 建议优先实现

第一优先级：

- Plugin manifest + package + Registry。
- install / enable / configure 状态模型。
- Capability Index。
- Capability Resolver。
- Policy Engine。
- Credential Broker。
- Tool Invocation Gateway。
- OpenAPI Runtime。
- HTTP MCP Runtime。
- Skill Context API。
- Audit / Langfuse trace。

第二优先级：

- Runtime Host for stdio MCP。
- Native Tool worker。
- Deferred Tool Schema Loading。
- Result paging / result_id。
- Plugin signing / review / allowlist。
- Runtime health and watchdog。

第三优先级：

- Trigger Plugin。
- Data Source pipeline 深度集成。
- Hook Plugin，但必须受控。
- Agent Template / Subagent Plugin。
- Marketplace 推荐和自动安装。

## 11. 参考资料

- OpenAI Codex Plugins: https://developers.openai.com/codex/plugins
- OpenAI Build Codex Plugins: https://developers.openai.com/codex/plugins/build
- OpenAI Codex App Server API overview: https://developers.openai.com/codex/app-server
- OpenAI Tool Search: https://developers.openai.com/api/docs/guides/tools-tool-search
- Claude Code Plugins Reference: https://code.claude.com/docs/en/plugins-reference
- Claude Code Agent SDK Plugins: https://code.claude.com/docs/en/agent-sdk/plugins
- Dify Plugin Introduction: https://docs.dify.ai/en/develop-plugin/getting-started/getting-started-dify-plugin
- Dify Tool Plugin: https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin
- Dify Data Source Plugin: https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/datasource-plugin
- Dify Trigger Plugin: https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/trigger-plugin
- Dify Agent Strategy Plugin: https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/agent-strategy-plugin
- Dify Plugin Daemon: https://github.com/langgenius/dify-plugin-daemon
- Dify Plugin Daemon Architecture: https://deepwiki.com/langgenius/dify-plugin-daemon/1.1-architecture
- Dify Plugin Lifecycle: https://deepwiki.com/langgenius/dify-plugin-daemon/1.2-plugin-system
- Open WebUI Extensibility: https://docs.openwebui.com/features/extensibility/
- Open WebUI Tools & Functions: https://docs.openwebui.com/features/extensibility/plugin/
- Open WebUI MCP: https://docs.openwebui.com/features/mcp/
