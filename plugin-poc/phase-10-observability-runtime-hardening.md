# Phase 10: Observability And Runtime Hardening

Phase 10 adds runtime event records and timeout handling to the invocation gateway.

## Runtime Events

Every supported capability invocation writes `runtime_events.jsonl` with:

- plugin id and version
- capability id and type
- runtime name
- success flag
- error code
- duration

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-events \
  --state /tmp/plugin-poc-state
```

## Timeout Smoke Test

The POC supports deterministic timeout simulation:

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

Expected result:

```json
{
  "success": false,
  "error": {
    "code": "runtime_timeout"
  }
}
```

## Current Boundary

- Timeout is deterministic simulation for POC tests.
- Real subprocess/network cancellation should be implemented in the production Runtime Host.
- Metrics are stored as JSONL, not exported to Prometheus or tracing backends yet.
