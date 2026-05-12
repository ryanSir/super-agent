## Runtime Design

The MCP runtime is intentionally integrated behind the existing Tool Invocation Gateway:

1. Agent selects an enabled MCP capability.
2. Gateway runs the same enablement, policy, credential and audit path as local and OpenAPI tools.
3. Gateway dispatches MCP capabilities to `streamable_http_mcp`.
4. MCP runtime sends JSON-RPC requests to the configured endpoint.
5. Runtime parses either JSON or SSE `data:` JSON-RPC responses.
6. Gateway returns structured output and records the invocation result.

## Endpoint

The demo plugin uses this Streamable HTTP MCP endpoint:

`https://stage-ai-fabric.zhihuiya.com/logic-mcp/eureka_claw?APP_ID=Patsnap`

## Current POC Boundaries

- Credential configuration is checked by the platform path, but the credential is not yet exchanged into endpoint-specific auth headers.
- The runtime does not persist MCP session IDs.
- Tool schemas are discovered with `tools/list`, but not yet synchronized into the capability index as individual platform tools.
- The runtime is synchronous and returns the completed JSON-RPC result.

## Later Enhancements

- Add session initialization and session header persistence if required by target MCP servers.
- Convert discovered MCP tools into first-class capability index entries.
- Add stdio-to-HTTP adapter support.
- Add per-plugin auth header mapping.
- Add streaming result propagation to Agent Runtime.
