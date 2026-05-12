## Why

Data source capabilities were indexed but not callable. Phase 8 adds a minimal runtime so Agent invocation can query plugin-provided data sources through the same gateway.

## What Changes

- Add local JSON data source runtime.
- Add `list-data-sources` CLI command.
- Route `data_source` capability invocation through the gateway.
- Add usage docs and tests.
