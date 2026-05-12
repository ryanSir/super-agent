## Why

Phase 6 needs the POC to connect to a real Streamable HTTP MCP endpoint instead of only mocked local runtimes. This validates whether the plugin capability model can expose MCP tools to the Agent invocation path with acceptable changes to the existing gateway.

## What Changes

- Add a Streamable HTTP MCP runtime client.
- Support MCP `tools/list` for endpoint discovery and smoke verification.
- Support MCP `tools/call` through the existing Tool Invocation Gateway.
- Wire the demo plugin MCP capability to the provided stage endpoint.
- Document how to verify the real endpoint and how to invoke an MCP tool through the enabled plugin flow.

## Scope

This phase keeps the implementation as a POC-level runtime:

- Uses JSON-RPC over HTTP POST.
- Supports `application/json` and `text/event-stream` responses.
- Does not yet implement long-lived MCP sessions, OAuth token exchange, stdio MCP, or SSE streaming output consumption beyond parsing returned SSE data lines.
