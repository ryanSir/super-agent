## Why

The POC needs a Runtime Host lifecycle model before implementing deeper process isolation. Phase 9 introduces start, stop and health state plus stdio MCP adapter metadata.

## What Changes

- Add runtime host state file.
- Add start, stop and health CLI commands.
- Register stdio MCP adapter metadata from manifest entries.
- Add usage docs and tests.
