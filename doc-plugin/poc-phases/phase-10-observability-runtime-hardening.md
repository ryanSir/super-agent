# Phase 10：Observability 与 Runtime 稳定性说明

## 目标

Phase 10 在插件调用链路中补充运行时事件记录和超时保护，用来观察每次能力调用是否成功、由哪个 runtime 执行、耗时多少，以及失败时的错误类型。

这个阶段的重点不是做完整监控平台，而是先把 Plugin Runtime 最小可观测闭环打通，为后续接入 Langfuse、Prometheus、Tracing 或公司现有观测系统预留结构。

## 当前能力

Phase 10 覆盖以下能力：

- 每次支持的 capability 调用后写入 runtime event。
- event 中记录 plugin、capability、runtime、success、error code、duration。
- 支持通过 CLI 查看 runtime event。
- 支持调用级 timeout 参数。
- 支持通过 `simulate_delay_ms` 做稳定的超时验证。
- 成功和失败都会进入 Audit；已定位到具体 capability 的成功和失败会进入 Runtime Event。

## Runtime Event 记录内容

事件写入本地状态目录下的 `runtime_events.jsonl`。

每条事件包含：

| 字段 | 含义 |
| --- | --- |
| `created_at` | 事件创建时间 |
| `event_type` | 事件类型，当前为 `capability_invocation` |
| `plugin_id` | 插件 ID |
| `version` | 插件版本 |
| `capability_id` | 被调用的能力 ID |
| `capability_type` | 能力类型，例如 `tool`、`mcp`、`openapi`、`data_source` |
| `runtime` | 实际执行的 runtime |
| `success` | 调用是否成功 |
| `error_code` | 失败错误码，成功时为空 |
| `duration_ms` | 调用耗时 |

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

PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001

PYTHONPATH=plugin-poc python -m plugin_poc.cli configure-credential company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --values '{"client_id":"demo-client","client_secret":"demo-secret"}'
```

## 验证成功调用事件

执行一次 data source capability 调用：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.datasource.slack_messages \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"query":"plugin","limit":2}'
```

查看 runtime event：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-events \
  --state /tmp/plugin-poc-state
```

预期可以看到类似结果：

```json
{
  "event_type": "capability_invocation",
  "plugin_id": "company.slack-demo",
  "version": "1.0.0",
  "capability_id": "company.slack-demo.datasource.slack_messages",
  "capability_type": "data_source",
  "runtime": "local_data_source",
  "success": true,
  "error_code": null
}
```

## 验证超时保护

当前 POC 使用 `simulate_delay_ms` 做确定性超时模拟，方便本地测试和自动化回归。

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.tool.send_message \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --confirm-sensitive \
  --timeout-ms 100 \
  --input '{"channel_id":"C001","text":"hello","simulate_delay_ms":500}'
```

预期失败：

```json
{
  "success": false,
  "error": {
    "code": "runtime_timeout"
  }
}
```

再次查看 runtime event：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-events \
  --state /tmp/plugin-poc-state
```

预期最后一条事件包含：

```json
{
  "capability_id": "company.slack-demo.tool.send_message",
  "capability_type": "tool",
  "runtime": null,
  "success": false,
  "error_code": "runtime_timeout"
}
```

## Runtime Event 与 Audit 的区别

Audit 面向合规和调用审计，回答“谁在什么 workspace/agent 下调用了什么能力，成功还是失败”。

Runtime Event 面向运行时观测，回答“哪个插件能力由哪个 runtime 执行，耗时多少，运行是否成功”。

当前 POC 中：

- `audit_log.jsonl` 记录所有 invoke 尝试，包括 capability 不存在、权限失败、credential 缺失等。
- `runtime_events.jsonl` 记录已经定位到 capability 的运行时事件。
- credential secret 不会写入 audit，也不会写入 runtime event。
- input 原文不会写入 audit；runtime event 也不记录 input。

## 当前边界

当前 Phase 10 仍是 POC 级实现：

- runtime event 暂时写入本地 JSONL 文件。
- timeout 是确定性模拟，不是真实进程取消或网络请求取消。
- 没有接入指标聚合、分布式 tracing、告警系统。
- 没有做 runtime 熔断、重试、限流、隔离队列。
- 没有区分平台错误、插件错误、外部系统错误的完整错误分层。

生产版本中，建议把 Runtime Host 作为主要治理点，在这里补齐真实 timeout、取消、重试、限流、隔离、指标、日志和 tracing。

## 代码位置

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/core/observability.py` | Runtime Event 写入和查询 |
| `plugin_poc/core/gateway.py` | 在统一 invoke 链路中写入 audit 和 runtime event |
| `plugin_poc/core/audit.py` | 调用审计记录 |
| `plugin_poc/runtime_host/host.py` | Runtime Host 启停和健康检查 |
| `plugin_poc/cli.py` | `list-events`、`invoke`、`runtime-health` 等 CLI 入口 |

## 与后续阶段的关系

Phase 10 提供的是本地观测骨架。后续正式产品化时，可以在不改变 Agent 调用入口的前提下，把本地 JSONL 替换或扩展为：

- Langfuse trace / span。
- Prometheus metrics。
- OpenTelemetry tracing。
- 平台统一日志。
- Runtime Host 健康检查和告警。
- 插件级调用成功率、耗时、错误码统计。
