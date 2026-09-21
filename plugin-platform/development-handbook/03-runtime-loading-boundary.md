# 03. 运行时加载边界：后台管理、桌面端和 Web Agent

本文说明 Plugin Platform、桌面端插件管理页和 Web / 业务 Agent Runtime 的职责边界。

## 1. 核心结论

Plugin Platform 当前定位为插件控制面，不直接承担所有插件能力的执行。

```text
Plugin Platform
  -> 管理插件包、版本、发布、安装、启用、包下载和能力声明

Desktop Runtime / Business Agent Runtime
  -> 加载插件包内的 skill / MCP / OpenAPI
  -> 注入 Agent session
  -> 根据自己的编排逻辑执行能力
```

后台管理平台只控制整个 plugin 是否可用。  
Skill、MCP、OpenAPI 等子能力的本地启用、禁用由桌面端或业务 Agent Runtime 自己控制。

## 2. 为什么不在后台做单能力开关

参考 Codex / Claude Code 的插件模型，平台和客户端职责不同：

| 层级 | 负责内容 |
| --- | --- |
| 后台管理平台 | 插件是否发布、是否安装到平台、是否整体启用 |
| 桌面端插件管理页 | 用户本地是否安装插件、是否启用插件、启用哪些 skill / MCP |
| Web / 业务 Agent Runtime | 服务端运行时装配哪些 plugin 能力进入当前 Agent |

后台如果控制到每个 skill / MCP，会和桌面端本地插件管理页冲突，也会让平台提前承担客户端偏好和会话级决策。

因此当前原则是：

```text
平台 enabled = 插件包允许被客户端下载和使用
客户端 enabled = 当前客户端是否安装并加载这个插件
客户端 capability state = 当前客户端加载哪些 skill / MCP / OpenAPI
```

平台是上限，客户端是本地选择。

## 3. 后台管理平台流程

后台管理平台负责：

```text
validate
  -> package
  -> publish
  -> install
  -> enable plugin
```

含义：

| 动作 | 含义 |
| --- | --- |
| validate | 校验插件目录和 `plugin.yaml` |
| package | 生成插件 zip 包 |
| publish | 发布插件版本到 Registry |
| install | 将插件版本加入平台安装状态 |
| enable | 允许该插件包被运行端加载 |

后台管理平台不负责：

- 用户桌面端是否安装插件。
- 用户本地是否启用某个 skill。
- 用户本地是否连接某个 MCP server。
- 当前 Agent session 是否使用某个能力。

## 4. 桌面端 Runtime 流程

桌面端应该有自己的插件管理页，类似 Codex / Claude Code。

推荐流程：

```text
用户打开桌面端 Plugin 页面
  -> 登录平台
  -> 拉取平台可用插件列表
  -> 用户点击 Install
  -> 下载插件 zip
  -> 校验 checksum
  -> 解压到本地 cache
  -> 写本地 installed 状态
  -> 用户点击 Enable
  -> 桌面端读取 plugin.yaml
  -> 加载本地启用的 skills / MCP / OpenAPI
  -> 注入当前 Agent session
```

本地 cache 示例：

```text
~/.your-agent/plugins/cache/
  research-assistant/
    0.1.0/
      plugin.yaml
      skills/
      openapi/
      mcp/
      credentials/
```

本地状态示例：

```json
{
  "plugins": {
    "research-assistant@0.1.0": {
      "installed": true,
      "enabled": true,
      "capability_states": {
        "skill:research-summary": true,
        "openapi:patent-search": false,
        "mcp:literature-mcp": true
      }
    }
  }
}
```

桌面端可以在本地关闭某个 skill / MCP，但不能打开平台未启用的 plugin。

## 5. Web / 业务 Agent Runtime 流程

Web 端不建议让浏览器直接下载并执行插件包。

推荐流程：

```text
Web UI
  -> 业务 Agent Backend
  -> 调用 Plugin Platform runtime loading API
  -> 拉取可用 plugin / skill / MCP / OpenAPI 资源
  -> 业务 Agent Backend 装配 Agent tools / context
  -> Agent 自己执行编排和工具调用
```

Web / 业务 Agent Runtime 可以选择：

- 直接拉取 skill markdown，注入上下文。
- 拉取 MCP config，注册 MCP client。
- 拉取 OpenAPI spec，转换成工具 schema。

## 6. Plugin Platform 应提供的 Runtime Loading API

后续建议新增：

```text
GET /api/runtime/plugins
GET /api/runtime/plugins/{plugin_id}
GET /api/runtime/plugins/{plugin_id}/package
GET /api/runtime/plugins/{plugin_id}/skills/{skill_name}/context
GET /api/runtime/plugins/{plugin_id}/mcp-servers
GET /api/runtime/plugins/{plugin_id}/openapi/{capability_name}
```

这些接口的职责不是执行插件能力，而是把平台已启用插件的加载信息提供给运行端。

## 7. 当前代码状态

当前已实现：

- Registry 发布。
- 插件安装。
- 插件整体启用 / 禁用。
- Capability Index：插件启用后返回该插件全部能力声明。
- Admin Console 基础管理。

当前未实现：

- 桌面端本地 cache。
- 桌面端本地插件管理页。
- Runtime Loading API。
- Web / 业务 Agent Runtime 装配协议。
- package 下载 API。

## 8. 后续建议

下一阶段优先做 Runtime Loading API，而不是中心化 Invocation Gateway。

推荐顺序：

1. `GET /api/runtime/plugins`：返回平台已启用插件列表。
2. `GET /api/runtime/plugins/{plugin_id}`：返回 plugin runtime manifest。
3. `GET /api/runtime/plugins/{plugin_id}/package`：支持桌面端下载 zip。
4. `GET /api/runtime/plugins/{plugin_id}/skills/{name}/context`：支持按需加载 skill。
5. `GET /api/runtime/plugins/{plugin_id}/mcp-servers`：支持运行端注册 MCP。
6. `GET /api/runtime/plugins/{plugin_id}/openapi/{name}`：支持运行端加载 OpenAPI spec。

