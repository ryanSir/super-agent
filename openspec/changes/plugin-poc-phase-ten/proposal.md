## Why

The POC has audit logs, but runtime-level observability and timeout behavior are still missing. Phase 10 adds runtime events and deterministic timeout handling.

## What Changes

- Add runtime event JSONL log.
- Write runtime events from gateway invocations.
- Add `list-events` CLI command.
- Add `--timeout-ms` invocation option with deterministic timeout simulation.
- Add usage docs and tests.
