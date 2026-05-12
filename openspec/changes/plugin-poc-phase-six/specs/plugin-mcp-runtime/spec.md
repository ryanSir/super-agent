## ADDED Requirements

### Requirement: Streamable HTTP MCP Tool Discovery

The POC SHALL provide a command that lists tools from a Streamable HTTP MCP endpoint.

#### Scenario: List tools from MCP endpoint

- **WHEN** the user runs `mcp-list-tools` with an endpoint
- **THEN** the CLI SHALL POST a JSON-RPC `tools/list` request
- **AND** parse JSON or SSE JSON-RPC responses
- **AND** return the discovered tools as JSON

### Requirement: MCP Capability Invocation

The POC SHALL invoke an enabled MCP capability through the same gateway path as other capabilities.

#### Scenario: Invoke MCP tool through gateway

- **GIVEN** a plugin with an enabled MCP capability
- **AND** required credentials have been configured for the workspace
- **WHEN** the user invokes the capability with `tool_name` and `arguments`
- **THEN** the gateway SHALL perform policy and credential checks
- **AND** dispatch the call to the Streamable HTTP MCP runtime
- **AND** return the MCP `tools/call` result
- **AND** write an audit record

### Requirement: MCP Error Handling

The POC SHALL return structured errors for MCP request and input failures.

#### Scenario: Missing tool name

- **WHEN** MCP invocation input does not include `tool_name`
- **THEN** invocation SHALL fail with an `invalid_input` error

#### Scenario: Endpoint request failure

- **WHEN** the MCP endpoint request fails
- **THEN** the CLI SHALL return a JSON error instead of a Python traceback
