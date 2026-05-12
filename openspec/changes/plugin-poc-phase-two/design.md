## Context

Phase 1 产物已经提供本地文件型 Registry：

```text
registry/
├── index.json
└── packages/<plugin_id>/<version>/
    ├── package.zip
    ├── metadata.json
    └── manifest.yaml
```

Phase 2 在此基础上新增一个本地 workspace 状态目录，用于模拟平台内的 Plugin Manager 状态和 Capability Index。

## Goals / Non-Goals

**Goals:**

- 从 Registry 安装指定插件版本。
- 启用插件并绑定到 workspace/agent。
- 禁用和卸载插件。
- 从已启用插件生成 Capability Index。
- 支持查询当前 workspace/agent 可用能力。

**Non-Goals:**

- 不做 runtime 执行。
- 不做 credential 配置。
- 不做权限策略。
- 不做服务化 API。

## Decisions

### Decision 1: 使用本地 state 目录模拟平台安装状态

第一版使用 `--state <state_dir>` 参数指定平台状态目录：

```text
state/
├── installed_plugins.json
├── enabled_plugins.json
├── capability_index.json
└── installed/
    └── <plugin_id>/<version>/
        ├── package.zip
        ├── metadata.json
        ├── manifest.yaml
        └── source/
```

原因：本期仍是 POC，不需要数据库。JSON 文件便于检查、测试和后续迁移。

### Decision 2: enable 时生成 Capability Index

安装只表示插件包进入平台；启用才表示插件能力对 workspace/agent 可见。`enable` 命令会解析 manifest capabilities 并写入 `capability_index.json`。

### Decision 3: Capability ID 使用稳定命名

能力 ID 格式：

```text
<plugin_id>.<capability_type>.<capability_name>
```

示例：

```text
company.slack-demo.tool.send_message
company.slack-demo.skill.summarize-channel
company.slack-demo.openapi.slack-demo-api
company.slack-demo.datasource.slack_messages
company.slack-demo.mcp.slack-demo-mcp
```

## Risks / Trade-offs

- [Risk] JSON state 不适合并发写 → POC 阶段接受，后续替换为 DB。
- [Risk] capability 解析只覆盖声明层，不验证真实 runtime → Phase 3 再做调用链路。
- [Risk] workspace/agent 只是字符串上下文 → 后续接入真实平台租户模型。

## Migration Plan

无迁移。Phase 2 新增 `state` 目录，删除即可回滚。

