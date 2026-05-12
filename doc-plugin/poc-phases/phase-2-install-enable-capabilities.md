# Phase 2：安装、启用与能力索引使用说明

## 当前能力

Phase 2 在 Phase 1 的基础上新增：

```text
publish -> install -> enable -> list-capabilities
```

当前可以验证：

- 从本地 Registry 安装指定插件版本。
- 把插件启用到指定 workspace 和 agent。
- 解析插件 manifest，生成 Capability Index。
- 查询指定 workspace/agent 可用的 capabilities。
- 禁用插件后移除对应 capabilities。
- 卸载插件后移除安装状态和相关 capabilities。

当前仍不支持：

- credential 配置和 test connection
- Policy Engine 权限校验
- Runtime Host 执行插件
- OpenAPI/MCP 真实调用
- Agent Runtime 主链路接入

## 新增文件说明

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/manager.py` | Plugin Manager，本地安装、启用、禁用、卸载、查询 installed plugins 和 capabilities |
| `plugin_poc/capability.py` | Capability Index 构建和过滤逻辑，从 manifest 子文件解析 tools、skills、openapi、mcp、data_sources |

## 本地状态目录

Phase 2 使用 `--state <state_dir>` 模拟平台插件安装状态。

安装和启用后，状态目录结构大概是：

```text
/tmp/plugin-poc-state/
├── installed_plugins.json
├── enabled_plugins.json
├── capability_index.json
└── installed/
    └── company.slack-demo/
        └── 1.0.0/
            ├── package.zip
            ├── metadata.json
            ├── manifest.yaml
            └── source/
```

这些文件含义：

| 文件 | 作用 |
| --- | --- |
| `installed_plugins.json` | 已安装插件版本列表 |
| `enabled_plugins.json` | workspace/agent 维度的启用绑定 |
| `capability_index.json` | 已启用插件暴露给 Agent 的能力索引 |
| `installed/<plugin>/<version>/source/` | 从 package.zip 解出的插件源码 |

## 1. 准备 Registry

先把示例插件发布到本地 Registry：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-registry \
  --force
```

## 2. 安装插件

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state
```

预期输出：

```json
{
  "status": "ok",
  "installed": {
    "plugin_id": "company.slack-demo",
    "version": "1.0.0",
    "status": "installed"
  }
}
```

查看已安装插件：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-installed \
  --state /tmp/plugin-poc-state
```

## 3. 启用插件

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

启用后会写入：

- `enabled_plugins.json`
- `capability_index.json`

## 4. 查询能力

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-capabilities \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

预期会返回类似能力：

```text
company.slack-demo.tool.send_message
company.slack-demo.skill.summarize-channel
company.slack-demo.openapi.slack-demo-api
company.slack-demo.datasource.slack_messages
company.slack-demo.mcp.eureka-claw-mcp
```

这些能力只是“可发现能力”，还不会真实执行。

## 5. 禁用插件

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli disable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

禁用后再次查询：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-capabilities \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

预期返回空 capabilities。

## 6. 卸载插件

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli uninstall company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state
```

卸载会删除：

- installed 状态
- enabled 绑定
- capability index 中对应能力
- `installed/company.slack-demo/1.0.0/` 安装目录

## 7. 完整验证命令

```bash
rm -rf /tmp/plugin-poc-registry /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-registry \
  --force

PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001

PYTHONPATH=plugin-poc python -m plugin_poc.cli list-capabilities \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

## 8. Phase 2 的边界

Phase 2 完成的是：

```text
Registry 中的插件包
  ↓ install
本地安装状态
  ↓ enable
workspace/agent 绑定
  ↓ build Capability Index
Agent 可发现能力
```

Phase 3 才会继续做：

```text
Tool Invocation Gateway
  ↓
OpenAPI Runtime / MCP Runtime
  ↓
真实调用插件能力
```
