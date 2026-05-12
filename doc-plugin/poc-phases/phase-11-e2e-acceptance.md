# Phase 11：E2E 验收说明

## 目标

Phase 11 提供一个本地端到端验收命令，用来验证 Plugin POC 从开发者发布插件，到 Agent 调用插件能力的主链路是否完整可用。

这个阶段不是新增一种插件能力，而是把前面阶段已经完成的能力串起来，形成一个稳定的回归验证入口。

## 验收链路

`run-e2e` 会自动执行以下步骤：

1. 发布插件到本地 Registry。
2. 从 Registry 安装插件到本地状态目录。
3. 在指定 workspace 和 agent 下启用插件。
4. 配置插件 credential。
5. 启动 Plugin Runtime Host。
6. 调用 tool capability。
7. 调用 data source capability。
8. 渲染 skill context。
9. 检查 runtime health。
10. 返回统一验收结果。

对应到整体架构，这条链路覆盖：

```text
Plugin SDK / CLI
  ↓
Plugin Registry
  ↓
Plugin Manager
  ↓
Capability Index
  ↓
Credential / Policy
  ↓
Tool Invocation Gateway
  ↓
Runtime Host
  ↓
Tool Runtime / Data Source Runtime / Skill Runtime
  ↓
Audit / Health
```

## 执行命令

```bash
rm -rf /tmp/plugin-poc-e2e-registry /tmp/plugin-poc-e2e-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli run-e2e \
  --plugin-dir plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-e2e-registry \
  --state /tmp/plugin-poc-e2e-state
```

## 预期结果

命令成功时，顶层结果应该包含：

```json
{
  "status": "ok",
  "publish": {
    "plugin_id": "company.slack-demo",
    "version": "1.0.0"
  },
  "capability_count": 4
}
```

其中还会返回：

- `install`：插件安装结果。
- `enable`：插件启用结果。
- `credential`：credential 配置结果，secret 字段会被脱敏。
- `runtime`：Runtime Host 启动结果。
- `health`：Runtime Host 健康状态。
- `tool_invocation`：tool capability 调用结果。
- `data_source_invocation`：data source capability 调用结果。
- `skill_context`：skill runtime 渲染出的 Agent 上下文片段。

## 验收通过标准

满足以下条件即可认为 Phase 11 验收通过：

- `status` 返回 `ok`。
- 插件能够被发布、安装、启用。
- credential 能够配置成功，并且输出中不暴露 secret 原文。
- Runtime Host 能够启动，并能返回 health。
- tool capability 调用成功。
- data source capability 调用成功。
- skill context 能够正常渲染。
- 过程中没有抛出未捕获异常。

## 当前边界

本地 E2E 默认不调用真实外部 MCP endpoint，也不调用真实 SaaS API。原因是本命令用于稳定回归验证，应该尽量避免依赖外部网络、外部系统状态或测试账号状态。

真实 Streamable HTTP MCP endpoint 已经在 Phase 6 中单独验证。后续如果需要做集成环境验收，可以再增加一个独立的 `run-integration-e2e`，专门用于连接真实 MCP、真实 OpenAPI 服务和真实观测后端。

## 代码位置

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/acceptance/e2e.py` | E2E 验收编排逻辑 |
| `plugin_poc/cli.py` | `run-e2e` 命令入口 |
| `plugin_poc/runtime_host/host.py` | Runtime Host 启动、停止、健康检查 |
| `plugin_poc/core/gateway.py` | 统一能力调用入口 |

## 与前面阶段的关系

Phase 11 依赖前面阶段的能力，不替代前面阶段的单项验证：

- Phase 1-2 验证插件规范、打包、发布、安装、启用。
- Phase 3-4 验证调用网关、credential、policy、audit。
- Phase 5-8 验证 OpenAPI、MCP、skill、data source runtime。
- Phase 9-10 验证 Runtime Host、观测事件和 Admin Console API。
- Phase 11 验证主链路能否串起来。

因此，日常开发时可以优先跑 Phase 11；如果失败，再回到对应阶段文档定位具体模块。
