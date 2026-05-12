# Phase 11: E2E Acceptance

Phase 11 adds a local end-to-end acceptance command.

It runs:

1. publish
2. install
3. enable
4. configure credential
5. start runtime
6. invoke tool capability
7. invoke data source capability
8. render skill context
9. check runtime health

## Use

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli run-e2e \
  --plugin-dir plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-e2e-registry \
  --state /tmp/plugin-poc-e2e-state
```

Expected result:

```json
{
  "status": "ok"
}
```

## Current Boundary

This local E2E command does not call the real Streamable HTTP MCP endpoint by default. Phase 6 already verified the real endpoint separately. Keeping E2E local makes regression checks stable and fast.
