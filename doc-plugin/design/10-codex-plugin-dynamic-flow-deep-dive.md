# 10. Codex Plugin 动态加载与执行链路深度分析

## 1. 分析目标

本文专门拆解 Codex 的整体插件流程，重点回答：

- Codex 如何发现 plugin、marketplace、skills、MCP、apps、hooks。
- plugin install / enable 后，运行时到底加载了什么。
- Agent 每一轮对话如何动态注入 plugin、skill、MCP tool、app connector。
- MCP tool schema 何时直接暴露，何时 deferred loading。
- 显式 `@plugin`、`$skill`、隐式 skill、tool_search、dynamic tool 的调用链路分别是什么。
- 这些机制对我们自研企业 Plugin 平台有什么可复用的设计。

本文基于官方文档和 `openai/codex` 当前源码结构推导。官方文档用于确认公开行为，源码用于理解实现分层和动态处理路径。

## 2. Codex Plugin 的核心抽象

Codex 里 plugin 不是单个 tool，而是一个本地可安装的能力包。官方定义里 plugin 可以包含：

```text
Plugin
  -> skills
  -> apps / connectors
  -> MCP servers
  -> hooks
  -> assets / marketplace metadata
```

对应目录结构：

```text
my-plugin/
  .codex-plugin/
    plugin.json           # 必需 manifest
  skills/
    <skill>/
      SKILL.md            # 可选：任务工作流
  hooks/
    hooks.json            # 可选：生命周期 hook
  .mcp.json               # 可选：MCP server 配置
  .app.json               # 可选：app connector 映射
  assets/                 # 可选：icon/logo/screenshot
```

源码中的主要模块边界：

| 模块 | 作用 |
| --- | --- |
| `codex-rs/core-plugins` | plugin marketplace、install、cache、load、manifest、startup sync |
| `codex-rs/plugin` | plugin id、loaded plugin、load outcome 等基础模型 |
| `codex-rs/core-skills` | skill 扫描、加载、缓存、上下文预算、显式/隐式注入 |
| `codex-rs/core/src/plugins` | plugin prompt rendering、显式 plugin mention 注入 |
| `codex-rs/core/src/mcp_tool_exposure.rs` | MCP tool 直接暴露或 deferred 暴露策略 |
| `codex-rs/core/src/tools/handlers/tool_search.rs` | client-executed tool search 的本地检索执行 |
| `codex-rs/app-server` | JSON-RPC API，暴露 plugin/list、plugin/install、skills/list、mcpServer/tool/call 等 |
| `codex-rs/hooks` | hooks 发现、信任、事件执行 |
| `codex-rs/rmcp-client` / `codex-rs/codex-mcp` | MCP server 连接、tool/resource 调用、OAuth |

## 3. Codex 插件链路总览

Codex 的完整 plugin 链路可以拆成 6 段：

```text
1. Marketplace discovery
   -> 官方 / repo / user / git / remote marketplace

2. Plugin install
   -> materialize source
   -> copy to ~/.codex/plugins/cache/<marketplace>/<plugin>/<version>
   -> write ~/.codex/config.toml enabled = true

3. Startup / config refresh
   -> sync curated repo
   -> auto-upgrade configured marketplace
   -> refresh remote installed plugin cache
   -> refresh installed plugin bundles

4. Runtime load
   -> read config plugins table
   -> load installed plugin root
   -> parse plugin.json
   -> load skills / MCP / apps / hooks
   -> produce PluginLoadOutcome

5. Turn preparation
   -> build available plugin instructions
   -> build available skills list with budget
   -> resolve explicit @plugin / $skill / app mentions
   -> list MCP tools
   -> decide direct tools vs deferred tools
   -> build ToolRouter

6. Tool / skill execution
   -> model invokes function / tool_search / MCP / dynamic tool
   -> ToolRouter dispatch
   -> hook interception / approval / MCP call / app call
   -> result returns to model
```

关键点：Codex 的动态处理并不是“启动时把所有 plugin 内容都塞给模型”，而是把 plugin 先加载成本地 runtime state，再按 turn 和按模型选择逐步暴露。

## 4. Marketplace Discovery

### 4.1 marketplace 来源

官方文档说明 Codex 可以读取这些 marketplace：

```text
official curated plugin directory
$REPO_ROOT/.agents/plugins/marketplace.json
$REPO_ROOT/.claude-plugin/marketplace.json
~/.agents/plugins/marketplace.json
configured Git marketplace
remote catalog marketplace
```

典型 marketplace entry：

```json
{
  "name": "my-plugin",
  "source": {
    "source": "local",
    "path": "./plugins/my-plugin"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

这里有两个设计点：

1. marketplace 只负责“可发现、可安装、策略、展示”，不是运行时。
2. `source.path` 指向插件源目录，但安装后 Codex 运行的是 cache 里的副本。

### 4.2 App Server 的 discovery API

Codex App Server 暴露：

```text
plugin/list
plugin/read
plugin/install
plugin/uninstall
marketplace/add
marketplace/upgrade
```

`plugin/list` 的源码路径：

```text
codex-rs/app-server/src/request_processors/plugins.rs
  -> plugin_list()
  -> plugin_list_response()
```

其关键逻辑：

```text
plugin/list
  -> load_latest_config()
  -> check Feature::Plugins
  -> check workspace_codex_plugins_enabled()
  -> maybe_start_plugin_list_background_tasks_for_config()
  -> list local marketplace
  -> optionally fetch remote marketplace
  -> fetch featured plugin ids
  -> return marketplaces + load errors + featured ids
```

源码里 `plugin_list_response()` 会先检查 plugins feature 和 workspace gate，再异步触发 background tasks：

```text
maybe_start_plugin_list_background_tasks_for_config()
  -> maybe_start_non_curated_plugin_cache_refresh()
  -> maybe_start_remote_installed_plugins_cache_refresh()
  -> maybe_start_remote_installed_plugin_bundle_sync()
```

这说明 Codex 的 marketplace listing 不只是读文件，还会顺手触发 cache refresh 和 remote sync。

## 5. Plugin Install

### 5.1 安装入口

App Server 安装入口：

```text
codex-rs/app-server/src/request_processors/plugins.rs
  -> plugin_install()
  -> plugin_install_response()
```

核心流程：

```text
plugin/install
  -> 校验 marketplacePath / remoteMarketplaceName 二选一
  -> load_latest_config()
  -> 校验 workspace 是否允许 plugins
  -> PluginsManager.install_plugin()
  -> reload config
  -> on_effective_plugins_changed()
  -> load plugin MCP servers
  -> 如 MCP 需要 OAuth，启动 OAuth login
  -> load plugin apps
  -> 判断 apps_needing_auth
  -> 返回 auth_policy + apps_needing_auth
```

这里很关键：安装不是单纯拷贝文件。安装完成后 Codex 会立即触发：

- 有效插件变更通知。
- MCP server OAuth 登录。
- app connector auth 检查。

### 5.2 PluginsManager.install_plugin

源码路径：

```text
codex-rs/core-plugins/src/manager.rs
  -> install_plugin()
  -> install_resolved_plugin()
```

核心流程：

```text
install_plugin(request)
  -> find_installable_marketplace_plugin(marketplace_path, plugin_name)
  -> install_resolved_plugin(resolved)

install_resolved_plugin(resolved)
  -> 判断 auth_policy
  -> 如果 openai-curated，读取 curated repo sha 作为 cache version
  -> materialize_marketplace_plugin_source()
  -> PluginStore.install() / install_with_version()
  -> set_user_plugin_enabled(..., true)
  -> track_plugin_installed()
  -> return PluginInstallOutcome
```

安装后会写用户配置：

```toml
[plugins."<plugin>@<marketplace>"]
enabled = true
```

插件包会进入 cache：

```text
~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/
```

### 5.3 为什么安装到 cache，而不是直接用 marketplace 源目录

这样做有几个效果：

1. marketplace 是 catalog/source，cache 是 runtime artifact。
2. Git marketplace 更新不会立刻破坏正在使用的 installed plugin。
3. curated plugin 可以用 repo sha 或短 sha 作为版本。
4. local plugin 也统一走 installed copy，减少源目录变更造成的运行时不确定性。

对我们平台的启发：

```text
Registry source package
  -> Installed artifact cache
  -> Enable state
  -> Runtime load from installed artifact
```

这比业务 Agent 直接读插件源目录更稳。

## 6. Startup Tasks

Codex App Server 初始化时会启动插件相关后台任务。

源码路径：

```text
codex-rs/app-server/src/message_processor.rs
  -> plugins_manager()
  -> maybe_start_plugin_startup_tasks_for_config()

codex-rs/core-plugins/src/manager.rs
  -> maybe_start_plugin_startup_tasks_for_config()
```

核心逻辑：

```text
if plugins_enabled:
  -> start_curated_repo_sync()
  -> spawn plugins-marketplace-auto-upgrade
  -> start_startup_remote_plugin_sync_once()
  -> maybe_start_remote_installed_plugins_cache_refresh()
  -> maybe_start_remote_installed_plugin_bundle_sync()
  -> warm featured_plugin_ids cache
```

这意味着 Codex 把插件系统拆成两类任务：

| 类型 | 说明 |
| --- | --- |
| foreground RPC | 用户显式 plugin/list、install、read、uninstall |
| background sync | curated repo、configured marketplace、remote installed、featured ids |

我们自研平台也应类似：Agent 调用链路不能阻塞在 marketplace 同步上，能力索引应提前刷新。

## 7. Runtime Load：把已安装 plugin 变成当前 session 能力

### 7.1 入口

源码路径：

```text
codex-rs/core-plugins/src/manager.rs
  -> plugins_for_config()
  -> plugins_for_config_with_force_reload()

codex-rs/core-plugins/src/loader.rs
  -> load_plugins_from_layer_stack()
  -> load_plugin()
```

调用链：

```text
plugins_for_config(config)
  -> 如果 plugins feature disabled，返回空
  -> 使用 config_version + plugin_hooks_enabled 查 cached_enabled_outcome
  -> 没命中缓存：
       load_plugins_from_layer_stack()
       log_plugin_load_errors()
       写入 cached_enabled_outcome
  -> 返回 PluginLoadOutcome
```

缓存 key 包括：

```text
config_version
plugin_hooks_enabled
```

这说明 plugin hooks 开关会影响 effective plugin outcome，因为 hooks 是否加载是 runtime state 的一部分。

### 7.2 load_plugins_from_layer_stack

核心逻辑：

```text
load_plugins_from_layer_stack(
  config_layer_stack,
  extra_plugins,
  store,
  restriction_product,
  plugin_hooks_enabled
)
  -> 从 user config 读取 [plugins] 表
  -> 合并 remote installed plugin configs
  -> 按 plugin key 排序
  -> 对每个 configured plugin 调 load_plugin()
  -> 检查 MCP server name 重名
  -> 返回 PluginLoadOutcome
```

注意：它读取的是 config layer stack 的 effective user config。也就是说插件 enable state 是用户配置态，不是每次从 marketplace 推导。

### 7.3 load_plugin 的详细步骤

源码路径：

```text
codex-rs/core-plugins/src/loader.rs
  -> load_plugin()
```

完整逻辑可概括为：

```text
load_plugin(config_name, plugin_config)
  -> parse PluginId: "<plugin>@<marketplace>"
  -> store.active_plugin_root(plugin_id)
  -> 构造 LoadedPlugin 初始结构
  -> 如果 plugin.enabled = false，直接返回 disabled LoadedPlugin
  -> 如果 active_plugin_root 不存在，error = "plugin is not installed"
  -> 校验 plugin_root 是目录
  -> load_plugin_manifest(plugin_root)
  -> 写 manifest_name / manifest_description
  -> 解析 skill roots
  -> load_plugin_skills()
  -> 解析 .mcp.json / manifest mcpServers
  -> 对 MCP server 应用 plugin_config 中的 per-server/per-tool policy
  -> load_plugin_apps()
  -> 如果 plugin_hooks_enabled:
       load_plugin_hooks()
  -> 返回 LoadedPlugin
```

### 7.4 manifest 解析

源码路径：

```text
codex-rs/core-plugins/src/manifest.rs
  -> load_plugin_manifest()
```

manifest 支持字段：

```text
name
version
description
keywords
skills
mcpServers
apps
hooks
interface
```

路径规则：

```text
skills      -> ./skills/
mcpServers  -> ./.mcp.json
apps        -> ./.app.json
hooks       -> ./hooks/hooks.json 或 inline object/list
assets      -> interface 里引用
```

源码里会对 manifest path 做规范化：路径必须解析到 plugin root 内部，避免插件通过 `../` 逃逸出安装目录。

### 7.5 LoadedPlugin 里到底有什么

`LoadedPlugin` 中的关键字段：

```text
config_name
manifest_name
manifest_description
root
enabled
skill_roots
disabled_skill_paths
has_enabled_skills
mcp_servers
apps
hook_sources
hook_load_warnings
error
```

这就是 Codex runtime 对插件的“能力索引”。模型不会直接看到这个结构，但后续 turn 会用它生成：

- available plugin summary。
- available skills list。
- MCP server/tool registry。
- plugin mention injection。
- hook source。
- app connector list。

## 8. Skill 动态加载链路

### 8.1 skill roots 来源

Codex skills 来自多个 scope：

```text
repo:   .agents/skills
user:   ~/.agents/skills
admin:  /etc/codex/skills
system: bundled system skills
plugin: ~/.codex/plugins/cache/.../<plugin>/skills
```

plugin skill root 由 `load_plugin()` 提供：

```text
plugin_skill_roots(plugin_root, manifest_paths)
  -> 默认 plugin_root/skills
  -> manifest.skills 指定路径
  -> sort + dedup
```

### 8.2 SkillsManager 缓存

源码路径：

```text
codex-rs/core-skills/src/manager.rs
  -> skills_for_config()
  -> skill_roots_for_config()
  -> build_skill_outcome()
```

缓存 key：

```text
roots: [(path, scope_rank, plugin_id)]
skill_config_rules
```

这能避免不同 session / role / plugin state 之间串缓存。

### 8.3 skill progressive disclosure

官方文档明确：Codex 初始只把每个 skill 的 name、description、file path 放入上下文，只有决定使用 skill 时才读取完整 `SKILL.md`。

源码里有预算控制：

```text
default_skill_metadata_budget(context_window)
  -> 有 context window：取 2%
  -> 没有 context window：默认 8000 characters
```

源码路径：

```text
codex-rs/core-skills/src/render.rs
  -> default_skill_metadata_budget()
  -> build_available_skills()
```

如果 skill 太多：

```text
1. 先缩短 description
2. 再移除 description
3. 仍超预算则省略部分 skill
4. 发 warning
```

### 8.4 每轮 turn 如何注入 skill

源码路径：

```text
codex-rs/core/src/session/turn.rs
  -> build_skills_and_plugins()
```

核心流程：

```text
turn/start
  -> loaded_plugins = plugins_manager.plugins_for_config()
  -> skills_outcome = turn_context.turn_skills.outcome
  -> collect_explicit_skill_mentions(input)
  -> maybe_prompt_and_install_mcp_dependencies()
  -> build_skill_injections()
  -> 把选中 skill 的完整 instructions 转成 ResponseItem
```

显式 skill 调用：

```text
用户输入 "$skill-name ..."
或 input item:
{
  "type": "skill",
  "name": "...",
  "path": ".../SKILL.md"
}
```

App Server 文档建议提供 `skill` input item，因为这样 server 可以直接注入完整 skill instructions，不需要模型靠 `$skill-name` 再定位，减少延迟和歧义。

### 8.5 plugin skill 命名空间

plugin skill 会带 plugin id。源码中 `plugin_namespace_for_skill_path()` 会从 skill path 向上找 `.codex-plugin/plugin.json` 或 `.claude-plugin/plugin.json`，得到 plugin namespace。

实际效果：

```text
普通 skill:      skill-name
plugin skill:    plugin-name:skill-name
```

这解决两个问题：

- 不同 plugin 的 skill 重名。
- 用户显式请求某个 plugin 的能力时，模型可以识别前缀。

## 9. Plugin Context 注入链路

### 9.1 session 级：Available Plugins Instructions

源码路径：

```text
codex-rs/core/src/context/available_plugins_instructions.rs
```

Codex 会把 enabled plugins 的 summary 注入 developer context：

```text
## Plugins
A plugin is a local bundle of skills, MCP servers, and apps...

### Available plugins
- `GitHub`: ...
- `Slack`: ...

### How to use plugins
- Discovery...
- Skill naming...
- Trigger rules...
- Relationship to capabilities...
```

这里注入的是 plugin summary，不是 plugin manifest 全量内容。

### 9.2 turn 级：显式 plugin mention injection

源码路径：

```text
codex-rs/core/src/session/turn.rs
  -> build_skills_and_plugins()

codex-rs/core/src/plugins/injection.rs
  -> build_plugin_injections()

codex-rs/core/src/plugins/render.rs
  -> render_explicit_plugin_instructions()
```

流程：

```text
用户显式提到 plugin / plugin:// mention
  -> collect_explicit_plugin_mentions()
  -> list_all_tools() 获取 MCP raw inventory
  -> merge plugin apps + accessible connectors
  -> build_plugin_injections()
  -> 生成 turn-scoped developer hint
```

生成的提示类似：

```text
Capabilities from the `GitHub` plugin:
- Skills from this plugin are prefixed with `GitHub:`.
- MCP servers from this plugin available in this session: `github`.
- Apps from this plugin available in this session: `GitHub`.
Use these plugin-associated capabilities to help solve the task.
```

这是一种很重要的动态策略：

- session 级只列 enabled plugin summary。
- turn 级只有显式提到 plugin 时，才补充这个 plugin 当前可用的 MCP/app/skill 路径。

## 10. MCP 动态加载与执行链路

### 10.1 plugin MCP 配置加载

plugin MCP 配置来自：

```text
manifest.mcpServers 指定路径
否则默认 plugin_root/.mcp.json
```

源码路径：

```text
codex-rs/core-plugins/src/loader.rs
  -> load_plugin_mcp_servers()
  -> load_mcp_servers_from_file()
  -> normalize_plugin_mcp_servers()
```

支持两种 `.mcp.json` 格式：

```json
{
  "docs": {
    "command": "docs-mcp",
    "args": ["--stdio"]
  }
}
```

或：

```json
{
  "mcp_servers": {
    "docs": {
      "command": "docs-mcp",
      "args": ["--stdio"]
    }
  }
}
```

加载后会叠加用户配置里的 plugin-scoped policy：

```toml
[plugins."my-plugin@test".mcp_servers.docs]
enabled = true
default_tools_approval_mode = "prompt"
enabled_tools = ["search"]
disabled_tools = ["delete"]

[plugins."my-plugin@test".mcp_servers.docs.tools.search]
approval_mode = "approve"
```

对应源码：

```text
apply_plugin_mcp_server_policy()
  -> enabled
  -> default_tools_approval_mode
  -> enabled_tools
  -> disabled_tools
  -> tools.<tool>.approval_mode
```

### 10.2 MCP server 何时启动/刷新

App Server API：

```text
config/mcpServer/reload
mcpServerStatus/list
mcpServer/resource/read
mcpServer/tool/call
mcpServer/oauth/login
mcpServer/startupStatus/updated
```

插件安装后：

```text
plugin_install_response()
  -> load_plugin_mcp_servers(installed_path)
  -> start_plugin_mcp_oauth_logins()
```

插件状态变化后：

```text
on_effective_plugins_changed()
  -> skills metadata invalidation
  -> MCP refresh callback
  -> app list/cache refresh
```

源码里 `effective_plugins_changed_callback()` 负责在插件变化时触发相关刷新。

### 10.3 每轮 turn 如何决定 MCP 工具暴露方式

源码路径：

```text
codex-rs/core/src/session/turn.rs
  -> built_tools()

codex-rs/core/src/mcp_tool_exposure.rs
  -> build_mcp_tool_exposure()
```

核心流程：

```text
built_tools()
  -> mcp_connection_manager.list_all_tools()
  -> loaded_plugins = plugins_manager.plugins_for_config()
  -> 如果 apps enabled:
       merge plugin apps + accessible connectors
  -> discoverable_tools for tool_suggest
  -> build_mcp_tool_exposure(all_mcp_tools, connectors, config, search_tool_enabled)
  -> ToolRouter::from_turn_context(...)
```

MCP tool 暴露规则：

```text
deferred_tools = 非 Codex Apps MCP tools
              + 已启用 connector 对应的 Codex Apps MCP tools

should_defer =
  search_tool_enabled
  && (
       Feature::ToolSearchAlwaysDeferMcpTools enabled
       || deferred_tools.len() >= 100
     )

if !should_defer:
  direct_tools = deferred_tools
  deferred_tools = None
else:
  direct_tools = []
  deferred_tools = Some(deferred_tools)
```

阈值：

```text
DIRECT_MCP_TOOL_EXPOSURE_THRESHOLD = 100
```

这就是 Codex 动态处理工具爆炸的关键实现：小工具集直接暴露；大工具集不直接暴露，而是交给 tool_search。

### 10.4 ToolRouter 中 MCP handler 注册

源码路径：

```text
codex-rs/core/src/tools/spec_plan.rs
  -> add_mcp_runtime_tools()
```

逻辑：

```text
if mcp_tools:
  for tool in mcp_tools:
    add_runtime(McpHandler::new(tool))

if deferred_mcp_tools:
  for tool in deferred_mcp_tools:
    add_runtime(McpHandler::with_exposure(tool, Deferred))
```

差异：

- direct MCP tools：schema 直接 model-visible。
- deferred MCP tools：runtime 已注册，但 schema 通过 tool_search 延迟加载。

## 11. tool_search 动态工具加载

### 11.1 官方机制

OpenAI `tool_search` 的机制是：

```text
初始 request:
  -> tools 中包含 tool_search
  -> 某些 function / namespace / MCP 标记 defer_loading = true

模型需要能力时:
  -> 生成 tool_search_call
  -> server 或 client 返回 tool_search_output
  -> output 中的 tools 变成后续可调用工具
```

官方建议：

- 优先用 namespace 或 MCP server 做高层描述。
- 初始只让模型看到 namespace/server name + description。
- 具体 function schema 延迟加载。
- 每个 namespace 尽量少于 10 个函数。
- 已加载工具跨 turn 可复用。

### 11.2 Codex 的 client-executed tool_search

源码路径：

```text
codex-rs/core/src/tools/handlers/tool_search.rs
```

`ToolSearchHandler` 内部使用 BM25：

```text
ToolSearchHandler::new(search_infos)
  -> entries: Vec<ToolSearchEntry>
  -> search_source_infos
  -> SearchEngineBuilder::with_documents(Language::English, documents)

handle(tool_search_call)
  -> parse query + limit
  -> BM25 search
  -> coalesce_loadable_tool_specs()
  -> return ToolSearchOutput { tools }
```

这说明 Codex 不是把所有 deferred tool 交给模型自己猜，而是在本地建立搜索索引，由模型发 query，Codex 返回匹配工具 schema。

### 11.3 tool_search 在 ToolRouter 里的位置

源码路径：

```text
codex-rs/core/src/tools/spec_plan.rs
  -> append_tool_search_executor()
```

`tool_search` 本身也是一个 tool executor。它的输入是 query/limit，输出是一批 `LoadableToolSpec`。

调用链：

```text
MCP tools 太多
  -> build_mcp_tool_exposure() 把 MCP tools 标记 deferred
  -> add_mcp_runtime_tools() 注册 deferred McpHandler
  -> append_tool_search_executor() 注册 ToolSearchHandler
  -> model 先看到 tool_search
  -> model 调 tool_search(query)
  -> ToolSearchHandler 返回相关 MCP namespace/function schema
  -> model 再调具体 MCP tool
  -> ToolRouter dispatch 到对应 McpHandler
```

### 11.4 对我们平台的直接映射

我们可以把 Codex 的 tool_search 模式平台化：

```text
Capability Index
  -> 建立 searchable capability entries
  -> 每个 entry 有 summary/search_text/tool_schema_ref

Agent 初始上下文
  -> 只注入 plugin/category/namespace summary
  -> 暴露 capability_search 工具

模型需要能力
  -> capability_search(query, limit)
  -> Resolver 返回 selected tool schemas
  -> 模型调用具体工具
```

企业版应加的治理：

```text
capability_search 前:
  -> tenant/workspace/agent/user policy filter
  -> credential readiness filter
  -> runtime health filter

capability_search 后:
  -> schema token budget
  -> tool allowlist
  -> audit "schema exposed"
```

## 12. Dynamic Tool 调用链路

Codex App Server 还有一套 experimental dynamic tool 机制。

官方文档里：

```text
dynamicTools on thread/start
  -> model 可调用 dynamic tool
  -> app-server 发 item/tool/call 给 client
  -> client 执行
  -> client 返回 DynamicToolCallResponse
  -> app-server submit Op::DynamicToolResponse
```

源码路径：

```text
codex-rs/app-server/src/dynamic_tools.rs
  -> on_call_response()
```

调用链：

```text
thread/start(dynamicTools)
  -> turn running
  -> model emits dynamicToolCall
  -> app-server emits:
       item/started(type=dynamicToolCall)
       item/tool/call server request
  -> client 返回 content_items + success
  -> on_call_response()
  -> conversation.submit(Op::DynamicToolResponse)
  -> model 继续
```

这和 plugin 不完全一样，但非常适合我们理解“动态执行外部能力”的另一种边界：Codex 允许 host app 临时注册工具，由 host client 执行，而不是安装成 plugin。

对我们平台的启发：

| Codex dynamic tool | 企业平台映射 |
| --- | --- |
| `dynamicTools` | turn-scoped ephemeral capability |
| `item/tool/call` | Runtime Host / Client Tool Request |
| client response | Tool Invocation Gateway callback |
| `DynamicToolResponse` | structured tool result |

## 13. Hooks 动态链路

### 13.1 hooks 来源

Codex hooks 来源：

```text
~/.codex/hooks.json
~/.codex/config.toml inline hooks
<repo>/.codex/hooks.json
<repo>/.codex/config.toml inline hooks
managed requirements.toml
enabled plugin bundled hooks
```

plugin hooks 默认关闭，需要：

```toml
[features]
plugin_hooks = true
```

### 13.2 plugin hooks 加载

源码路径：

```text
codex-rs/core-plugins/src/loader.rs
  -> load_plugin_hooks()
```

规则：

```text
if manifest.hooks exists:
  -> path / paths / inline object / inline list
else:
  -> plugin_root/hooks/hooks.json

hook source metadata:
  -> plugin_id
  -> plugin_root
  -> plugin_data_root
  -> source_path
  -> source_relative_path
  -> hooks
```

plugin hook 命令会收到环境变量：

```text
PLUGIN_ROOT
PLUGIN_DATA
CLAUDE_PLUGIN_ROOT
CLAUDE_PLUGIN_DATA
```

### 13.3 hooks 运行时

官方事件包括：

```text
SessionStart
UserPromptSubmit
PreToolUse
PermissionRequest
PostToolUse
Stop
```

动态链路：

```text
turn / tool event 发生
  -> hooks engine 找匹配 event + matcher
  -> 非 managed hooks 需要 trust review
  -> command hooks 并发启动
  -> hook stdin 接收事件 JSON
  -> hook stdout/stderr/exit code 影响上下文或权限决策
```

关键行为：

- `PreToolUse` 可 deny 支持的工具调用。
- `PermissionRequest` 可 allow / deny / defer to normal approval。
- `PostToolUse` 不能撤销已发生副作用，但可以替换工具结果或追加 context。
- `UserPromptSubmit` 可追加 developer context 或 block prompt。
- `Stop` 可让 Codex 继续跑一轮。

对我们平台的建议：MVP 不开放任意脚本 hook，但应保留内部 lifecycle event：

```text
BeforePrompt
BeforeToolCall
BeforePermissionRequest
AfterToolCall
AfterTurn
BeforeCompaction
AfterCompaction
```

## 14. App / Connector 动态链路

Codex plugin 可以通过 `.app.json` 指向 app connector。

加载链路：

```text
load_plugin_apps(plugin_root)
  -> manifest.apps 或默认 .app.json
  -> 读取 apps map
  -> 提取 app.id
  -> dedup
```

运行时：

```text
turn/start
  -> apps_enabled?
  -> mcp_connection_manager.list_all_tools()
  -> accessible_connectors_from_mcp_tools()
  -> merge_plugin_connectors_with_accessible(plugin.effective_apps)
  -> with_app_enabled_state(config)
  -> 显式 app mention 或 plugin mention 可启用相关 connector
```

App tool approval 走 connector 的 tool annotation 和本地 app config：

```toml
[apps.google_drive]
enabled = true
destructive_enabled = false
default_tools_approval_mode = "prompt"

[apps.google_drive.tools."files/delete"]
enabled = false
approval_mode = "approve"
```

对我们平台的映射：

```text
plugin .app.json
  -> external connector reference
  -> connector auth/install state
  -> per-tool destructive/open-world policy
  -> Tool Gateway approval
```

## 15. 一次 Codex Turn 的完整动态流程

下面按一次用户请求串起来。

### 15.1 turn/start 前

```text
Codex 启动
  -> load config layers
  -> start plugin startup tasks
  -> sync marketplaces / remote installed / featured ids
  -> MCP manager 按 config 准备 server 状态
```

### 15.2 用户发起 turn/start

```text
turn/start(input)
  -> 创建 TurnContext
  -> 读取 thread config snapshot
  -> SkillsManager.skills_for_config()
  -> PluginsManager.plugins_for_config()
```

### 15.3 构造上下文

```text
build_skills_and_plugins()
  -> loaded_plugins.capability_summaries()
  -> collect_explicit_plugin_mentions(input)
  -> 如 apps 或 plugin mention，需要 list_all_tools()
  -> merge plugin apps + accessible connectors
  -> collect_explicit_skill_mentions(input)
  -> build_skill_injections()
  -> build_plugin_injections()
  -> 返回 ResponseItems + explicitly_enabled_connectors
```

同时 session 级 context 会包含：

```text
AvailablePluginsInstructions
AvailableSkillsInstructions
```

但这些都是摘要和索引，不是完整 manifest / tools / skill docs。

### 15.4 构造工具路由

```text
built_tools()
  -> mcp_connection_manager.list_all_tools()
  -> loaded_plugins.effective_apps()
  -> connectors with enabled state
  -> discoverable_tools for suggestions
  -> build_mcp_tool_exposure()
  -> ToolRouter::from_turn_context()
```

ToolRouter 包含：

```text
model_visible_specs
registry
  -> built-in tools
  -> MCP handlers
  -> deferred MCP handlers
  -> tool_search handler
  -> dynamic tool handlers
  -> extension tool executors
```

### 15.5 模型第一次响应

模型可能：

```text
1. 直接回答
2. 调 direct tool
3. 调 tool_search
4. 调 dynamic tool
5. 调 MCP tool
6. 请求 user input / approval
```

### 15.6 如果是 tool_search

```text
model -> tool_search(query)
  -> ToolRouter.build_tool_call()
  -> ToolSearchHandler.handle()
  -> BM25 search deferred entries
  -> ToolSearchOutput { tools }
  -> tools 注入后续模型上下文
  -> model 再调用具体 tool
```

### 15.7 如果是 MCP tool

```text
model -> function call namespace=mcp__server__, name=tool
  -> ToolRouter.build_tool_call()
  -> McpHandler
  -> hook PreToolUse
  -> approval / policy
  -> mcp_connection_manager call tool
  -> hook PostToolUse
  -> result returned to model
```

### 15.8 如果是 skill

skill 不是 runtime tool。流程是：

```text
用户显式 $skill 或模型隐式匹配
  -> Codex 读取完整 SKILL.md
  -> 注入 developer context
  -> skill 内可能指导模型调用工具、读文件或执行脚本
```

### 15.9 如果是 plugin mention

plugin mention 也不是直接执行 plugin。流程是：

```text
用户 @plugin / plugin:// mention
  -> 解析 mentioned plugin
  -> 注入 "该 plugin 有哪些 skills/MCP/apps 可用"
  -> 模型再选择具体 skill/MCP/app/tool
```

这点非常重要：在 Codex 中 plugin 是能力包，不是一个可调用函数。

## 16. 动态处理机制总结

Codex 的“动态”主要体现在 8 个点：

| 动态点 | 实现方式 |
| --- | --- |
| marketplace 动态发现 | `plugin/list` 根据 cwd、user config、remote catalog 返回 |
| plugin 安装动态化 | install 时 materialize source 到 cache，写 config enabled |
| plugin runtime 动态加载 | `plugins_for_config()` 根据 config version 缓存和重载 |
| skill 动态注入 | 初始只展示 name/description/path，选中才加载完整 SKILL.md |
| plugin mention 动态注入 | 只有显式 mention plugin 时，补充其 MCP/app/skill 前缀 |
| MCP schema 动态暴露 | 工具少时 direct，工具多时 deferred |
| tool_search 动态加载 schema | BM25 搜索 deferred tools，返回可加载 tool specs |
| dynamicTools | host client 可按 thread 注册临时工具，由 app-server 转发执行 |

## 17. Codex 对我们平台最有价值的设计

### 17.1 Plugin 不是执行单元，而是能力包

Codex 中 plugin 只提供：

```text
summary
skills
MCP server config
app connector reference
hooks
assets
```

真正执行的是：

```text
Skill instructions
MCP tool
App connector tool
Hook command
Dynamic tool handler
Built-in tool
```

我们也应保持：

```text
Plugin = asset/governance boundary
Capability = runtime callable unit
Runtime Host = execution boundary
```

### 17.2 Enable state 和 runtime load 要分离

Codex：

```text
plugin installed in cache
plugin enabled in config.toml
plugins_for_config() loads enabled plugins
```

我们：

```text
plugin package in Registry
plugin installed in workspace
capability enabled for agent/user
Capability Resolver loads effective capabilities
```

### 17.3 按 turn 动态组装，而不是全局一次性注入

Codex 每轮 turn 都会结合：

```text
input mentions
current config
enabled apps
MCP server tools
skill config
plugin state
feature flags
```

生成当前轮真正可见的 context 和 tools。

我们平台也应该：

```text
每轮请求:
  -> Resolver(query, tenant, workspace, agent, user)
  -> top-k capabilities
  -> deferred schema
  -> per-turn tool router
```

### 17.4 token 控制要内建在能力发现层

Codex 已经内建：

- skill list 2% context budget / 8000 chars fallback。
- skill progressive disclosure。
- MCP direct exposure threshold 100。
- deferred tool_search。
- plugin summary 而非 full manifest 注入。

我们应该从第一版就设计：

```text
capability_summary_budget
tool_schema_budget
skill_context_budget
tool_result_budget
deferred_schema_loading
result_id / pagination
```

### 17.5 插件变更必须触发多类缓存失效

Codex install/uninstall 后会触发：

```text
on_effective_plugins_changed()
  -> clear plugin cache
  -> skills watcher reload
  -> MCP reload
  -> app/connector cache refresh
```

我们平台也要有：

```text
PluginEnabledChanged event
  -> Capability Index rebuild
  -> Runtime Host refresh
  -> Credential readiness refresh
  -> Agent tool cache invalidation
  -> Observability annotation
```

## 18. 建议我们落地的 Codex-style 流程

### 18.1 管理面

```text
Marketplace / Registry
  -> plugin/list
  -> plugin/read
  -> plugin/install
  -> install artifact cache
  -> enable/config state
  -> effective capabilities rebuild
```

### 18.2 调用面

```text
Agent turn
  -> load effective capability summaries
  -> inject plugin summaries
  -> inject skill summaries with budget
  -> collect explicit plugin/skill mentions
  -> capability_search if needed
  -> load selected tool schema
  -> Tool Gateway dispatch
```

### 18.3 动态工具加载

```text
CapabilitySearchHandler
  -> searchable entries from Capability Index
  -> BM25 / vector / hybrid search
  -> policy + credential + runtime health filter
  -> return loadable tool specs
```

### 18.4 Runtime Host

```text
OpenAPI / HTTP MCP:
  -> Gateway 直接调用

stdio MCP / native tool / hook command:
  -> Runtime Host
  -> process/container
  -> timeout/resource policy
  -> structured result
```

## 19. 参考资料与源码位置

官方资料：

- Codex Plugins: https://developers.openai.com/codex/plugins
- Build Codex Plugins: https://developers.openai.com/codex/plugins/build
- Codex App Server: https://developers.openai.com/codex/app-server
- Codex Configuration Reference: https://developers.openai.com/codex/config-reference
- Codex Skills: https://developers.openai.com/codex/skills
- Codex Hooks: https://developers.openai.com/codex/hooks
- OpenAI Tool Search: https://developers.openai.com/api/docs/guides/tools-tool-search

源码位置：

- `openai/codex/codex-rs/core-plugins/src/manager.rs`
- `openai/codex/codex-rs/core-plugins/src/loader.rs`
- `openai/codex/codex-rs/core-plugins/src/manifest.rs`
- `openai/codex/codex-rs/core-skills/src/manager.rs`
- `openai/codex/codex-rs/core-skills/src/render.rs`
- `openai/codex/codex-rs/core/src/session/turn.rs`
- `openai/codex/codex-rs/core/src/mcp_tool_exposure.rs`
- `openai/codex/codex-rs/core/src/tools/handlers/tool_search.rs`
- `openai/codex/codex-rs/core/src/plugins/injection.rs`
- `openai/codex/codex-rs/core/src/context/available_plugins_instructions.rs`
- `openai/codex/codex-rs/app-server/src/request_processors/plugins.rs`
- `openai/codex/codex-rs/app-server/src/dynamic_tools.rs`
