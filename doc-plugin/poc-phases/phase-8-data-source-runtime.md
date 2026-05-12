# Phase 8: Data Source Runtime

Phase 8 makes `data_source` capabilities callable through the same gateway used by tools, OpenAPI and MCP.

The POC supports a local JSON data source so the full query path can be tested without external services.

## Use

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-data-sources \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli invoke company.slack-demo.datasource.slack_messages \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --user user_001 \
  --input '{"query":"mcp","limit":1}'
```

## Current Boundary

- Supports `local_json` only.
- Supports simple full-record text matching, optional `channel_id`, and `limit`.
- Real database, API pagination and vector retrieval are later runtime extensions.
