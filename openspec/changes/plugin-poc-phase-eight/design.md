## Design

The runtime loads the data source YAML from the installed plugin source, then resolves a local JSON file path declared by the data source config.

The first implementation supports:

- `type: local_json`
- simple text query
- optional `channel_id`
- `limit`

This keeps the POC deterministic while preserving the capability shape for later API/database/vector backends.
