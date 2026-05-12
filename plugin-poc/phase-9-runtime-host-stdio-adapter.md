# Phase 9: Runtime Host And stdio Adapter PoC

Phase 9 adds a POC-level Runtime Host state model.

It can:

- start/register a plugin runtime
- stop a plugin runtime
- report runtime health
- register stdio MCP adapter metadata

## Use

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli start-runtime company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state
```

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli runtime-health \
  --state /tmp/plugin-poc-state \
  --plugin-id company.slack-demo \
  --version 1.0.0
```

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli stop-runtime company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state
```

## Current Boundary

The stdio MCP adapter is registered as metadata only:

```text
stdio command -> adapter endpoint mapping
```

It does not yet spawn a subprocess or proxy MCP traffic. That is the next deeper runtime implementation after this POC validates lifecycle and configuration shape.
