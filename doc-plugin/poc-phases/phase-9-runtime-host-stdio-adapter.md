# Phase 9：Runtime Host 与 stdio Adapter 说明

## 目标

Phase 9 引入 POC 级 Plugin Runtime Host 状态模型，用来验证插件运行时的生命周期管理和 stdio MCP adapter 的配置形态。

这个阶段重点不是实现完整的进程托管和 MCP 代理，而是先明确平台需要能管理哪些 runtime 状态：插件是否启动、运行模式是什么、注册了哪些 adapter、健康状态如何、是否可以停止。

## 当前能力

Phase 9 覆盖以下能力：

- 启动或注册某个插件的 Runtime Host。
- 停止某个插件的 Runtime Host。
- 查询单个插件 runtime health。
- 查询所有已注册 runtime。
- 从 manifest 中识别 `transport: stdio` 的 MCP 配置。
- 为 stdio MCP 生成 adapter endpoint 映射。
- 将 runtime 状态写入本地 `runtime_host.json`。

## Runtime Host 在当前 POC 中的含义

当前 POC 中，Runtime Host 是一个本地状态模型，用来模拟未来生产环境中的插件运行时控制面。

它负责记录：

| 字段 | 含义 |
| --- | --- |
| `plugin_id` | 插件 ID |
| `version` | 插件版本 |
| `mode` | 运行模式，默认是 `local_daemon` |
| `status` | 当前运行状态，例如 `running`、`stopped` |
| `started_at` | 启动时间 |
| `stopped_at` | 停止时间 |
| `health` | 健康状态 |
| `adapters` | 当前插件注册的 adapter 列表 |

注意：当前 Runtime Host 不是真实常驻服务，也不会真正 fork 子进程。它是为后续生产级 Runtime Host 设计验证生命周期、状态结构和 CLI 操作入口。

## stdio Adapter 在当前 POC 中的含义

有些 MCP Server 使用 stdio 方式启动，例如：

```yaml
capabilities:
  mcp:
    - name: local-stdio-demo
      transport: stdio
      command: python -m plugin_poc.demo_stdio_mcp
```

但是业务 Agent 或平台网关更适合通过 HTTP 方式调用能力。因此生产系统中通常需要一个 adapter，把 stdio MCP Server 包装成平台可访问的 HTTP endpoint。

当前 POC 先做 metadata 注册：

```text
stdio command
  ↓
adapter endpoint metadata
  ↓
runtime_host.json
```

示例映射：

```json
{
  "name": "local-stdio-demo",
  "transport": "stdio",
  "command": "python -m plugin_poc.demo_stdio_mcp",
  "adapter_endpoint": "http://127.0.0.1:8790/mcp/company.slack-demo/local-stdio-demo",
  "status": "registered"
}
```

## 准备插件状态

如果你已经按前面阶段准备过 `/tmp/plugin-poc-state`，可以跳过本节。

```bash
rm -rf /tmp/plugin-poc-registry /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-registry \
  --force

PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state
```

Phase 9 只验证 runtime 生命周期，所以不要求先 enable 到某个 workspace/agent，也不要求配置 credential。

## 启动 Runtime Host

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli start-runtime company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state
```

预期返回：

```json
{
  "status": "ok",
  "runtime": {
    "plugin_id": "company.slack-demo",
    "version": "1.0.0",
    "mode": "local_daemon",
    "status": "running",
    "health": "ok",
    "adapters": [
      {
        "name": "local-stdio-demo",
        "transport": "stdio",
        "command": "python -m plugin_poc.demo_stdio_mcp",
        "adapter_endpoint": "http://127.0.0.1:8790/mcp/company.slack-demo/local-stdio-demo",
        "status": "registered"
      }
    ]
  }
}
```

## 查询 Runtime Health

查询指定插件：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli runtime-health \
  --state /tmp/plugin-poc-state \
  --plugin-id company.slack-demo \
  --version 1.0.0
```

预期返回：

```json
{
  "status": "ok"
}
```

查询全部 runtime：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli runtime-health \
  --state /tmp/plugin-poc-state
```

## 停止 Runtime Host

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli stop-runtime company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state
```

预期返回：

```json
{
  "status": "ok",
  "runtime": {
    "plugin_id": "company.slack-demo",
    "version": "1.0.0",
    "status": "stopped",
    "health": "stopped"
  }
}
```

再次查询该插件 health 时，顶层状态应该是 `stopped`。

## 当前边界

当前 Phase 9 仍是 POC 级实现：

- 不会真实启动 stdio MCP 子进程。
- 不会真实代理 stdio MCP 到 HTTP。
- 不会做进程保活、重启、资源限制。
- 不会做并发 worker 池或队列调度。
- 不会做 runtime sandbox 隔离。
- 不会做 adapter endpoint 的真实网络监听。

这些能力属于生产级 Runtime Host 的后续实现范围。

## 后续生产实现建议

正式实现时，Runtime Host 至少需要补齐：

- 插件进程启动、停止、重启。
- stdio MCP 到 HTTP 或平台内部协议的 adapter。
- 进程健康检查和心跳。
- 超时、取消、重试、限流。
- stdout、stderr、调用日志采集。
- 插件级资源限制，例如 CPU、内存、并发数。
- 插件级隔离，例如容器、沙箱或独立 worker。
- 运行状态上报给 Plugin 核心服务。

## 代码位置

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/runtime_host/host.py` | Runtime Host 状态管理和 stdio adapter metadata 注册 |
| `plugin_poc/cli.py` | `start-runtime`、`stop-runtime`、`runtime-health` 命令入口 |
| `plugin_poc/management/capability.py` | 从 manifest 构建 MCP capability 索引 |
| `plugin_poc/demo_stdio_mcp.py` | POC 中的 stdio MCP demo 入口 |
| `examples/slack-demo/plugin.yaml` | 示例插件中的 `transport: stdio` 配置 |

## 与后续阶段的关系

Phase 9 解决的是 Runtime Host 生命周期和 adapter 配置形态。

Phase 10 在这个基础上补充 runtime event、timeout 和运行时观测能力。Phase 11 再把插件发布、安装、启用、credential、runtime、tool、data source、skill 串起来做端到端验收。
