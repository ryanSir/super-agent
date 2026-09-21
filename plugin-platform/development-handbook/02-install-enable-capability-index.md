# 02. 插件安装启用手册：Install、Enable 和 Capability Index

本文说明插件发布到 Registry 之后，平台如何安装、启用插件，并把插件能力暴露给后续调用方。

## 1. 本阶段目标

完成插件从“已发布”到“可被发现”的平台管理链路：

```text
publish
  -> install
  -> enable
  -> capabilities
```

这几个动作的边界是：

| 阶段 | 含义 |
| --- | --- |
| `publish` | 插件版本进入 Registry，平台知道有这个插件版本 |
| `install` | 从 Registry 选择一个插件版本，加入平台安装状态 |
| `enable` | 将已安装插件设为可用 |
| `capabilities` | 查询当前已启用插件暴露的能力 |

## 2. 前置条件

已经完成 M1：

1. 插件目录校验成功。
2. 插件已打包成 zip。
3. 插件已发布到 Registry。

可以先确认 Registry 中已有插件：

```bash
curl -sS http://127.0.0.1:8017/api/registry/plugins
```

## 3. Install：安装插件

安装插件表示：平台从 Registry 中选择一个已发布插件版本，并记录到安装状态中。

命令：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations \
  -H 'Content-Type: application/json' \
  -d '{"plugin_id":"research-assistant","version":"0.1.0"}'
```

成功返回：

```json
{
  "plugin_id": "research-assistant",
  "version": "0.1.0",
  "enabled": false
}
```

本地会生成安装记录：

```text
.plugin-platform-data/installations/research-assistant.json
```

注意：安装后默认 `enabled=false`，表示插件已安装，但能力尚未生效。

## 4. Enable：启用插件

启用插件表示：已安装插件可以进入 Capability Index。

命令：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations/enable \
  -H 'Content-Type: application/json' \
  -d '{"plugin_id":"research-assistant"}'
```

成功返回：

```json
{
  "plugin_id": "research-assistant",
  "version": "0.1.0",
  "enabled": true
}
```

启用后，安装记录中的状态会更新为：

```json
"enabled": true
```

## 5. Capabilities：查询能力索引

Capability Index 表示当前平台已启用插件暴露出的能力集合。

命令：

```bash
curl -sS http://127.0.0.1:8017/api/capabilities
```

如果 `research-assistant` 已启用，会返回类似能力：

```text
research-summary
patent-search
literature-mcp
```

这一步模拟未来业务 Agent 或其他调用方的能力发现过程。

## 6. Disable：禁用插件

禁用插件表示：插件仍然安装，但能力不再出现在 Capability Index 中。

命令：

```bash
curl -sS -X POST http://127.0.0.1:8017/api/manager/installations/disable \
  -H 'Content-Type: application/json' \
  -d '{"plugin_id":"research-assistant"}'
```

禁用后再次查询：

```bash
curl -sS http://127.0.0.1:8017/api/capabilities
```

应不再返回该插件的能力。

## 7. 本阶段执行链路

完整命令顺序：

```bash
curl -sS http://127.0.0.1:8017/api/registry/plugins

curl -sS -X POST http://127.0.0.1:8017/api/manager/installations \
  -H 'Content-Type: application/json' \
  -d '{"plugin_id":"research-assistant","version":"0.1.0"}'

curl -sS -X POST http://127.0.0.1:8017/api/manager/installations/enable \
  -H 'Content-Type: application/json' \
  -d '{"plugin_id":"research-assistant"}'

curl -sS http://127.0.0.1:8017/api/capabilities
```

## 8. 内部代码入口

| 代码 | 职责 |
| --- | --- |
| `services/plugin-core-service/plugin_core_service/api/manager_routes.py` | 安装、启用、禁用 API |
| `services/plugin-core-service/plugin_core_service/api/capability_routes.py` | 能力发现 API |
| `services/plugin-management-service/plugin_management_service/manager/service.py` | Plugin Manager 业务逻辑 |
| `services/plugin-management-service/plugin_management_service/manager/capability_index.py` | Capability Index 查询逻辑 |
| `services/plugin-management-service/plugin_management_service/storage/local_store.py` | 本地安装状态存储 |

## 9. 内部流程

安装流程：

```text
POST /api/manager/installations
  -> PluginManagerService.install(plugin_id, version)
  -> 检查 Registry 中是否存在该版本
  -> 创建 InstallationRecord(enabled=false)
  -> 写入 .plugin-platform-data/installations/{plugin_id}.json
```

启用流程：

```text
POST /api/manager/installations/enable
  -> PluginManagerService.enable(plugin_id)
  -> 读取 InstallationRecord
  -> 设置 enabled=true
  -> 保存安装状态
```

能力发现流程：

```text
GET /api/capabilities
  -> CapabilityIndexService.list_capabilities()
  -> 读取所有安装记录
  -> 过滤 enabled=true 的插件
  -> 从 Registry 读取插件版本能力声明
  -> 汇总返回 capabilities
```

## 10. 当前阶段边界

当前已支持：

- 全局安装状态。
- 安装、启用、禁用插件。
- 查询已启用能力。
- 本地 JSON 文件存储安装状态。

当前暂不支持：

- workspace / tenant 多租户作用域。
- agent 级能力绑定。
- 平台侧 capability 细粒度开关。
- 安装记录查询列表 API。
- 卸载插件。
- 版本升级策略。
- 权限校验和审计。
