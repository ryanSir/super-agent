## ADDED Requirements

### Requirement: Capability discovery API
The system SHALL expose API endpoints for external callers to discover enabled plugin capabilities.

#### Scenario: Discover workspace capabilities
- **WHEN** a caller provides a workspace id
- **THEN** the API SHALL return enabled capabilities from the workspace Capability Index

#### Scenario: Discover agent-bound capabilities
- **WHEN** a caller provides workspace id and agent id
- **THEN** the API SHALL return only capabilities enabled for that agent binding

### Requirement: Remote OpenAPI capability adapter
The system SHALL model OpenAPI capabilities as remote HTTP invocations.

#### Scenario: OpenAPI capability metadata
- **WHEN** an OpenAPI capability is indexed
- **THEN** invocation metadata SHALL include operation id, method, path, input schema reference, credential requirement, and timeout policy

#### Scenario: OpenAPI invocation timeout
- **WHEN** a remote OpenAPI call exceeds its configured timeout
- **THEN** the adapter SHALL return a structured timeout error and SHALL NOT hide it as a successful tool result

### Requirement: Streamable HTTP MCP capability adapter
The system SHALL support Streamable HTTP MCP capabilities and reject unsupported MCP transports in phase one.

#### Scenario: MCP initialize
- **WHEN** a Streamable HTTP MCP capability is used for the first time
- **THEN** the adapter SHALL initialize a session using the configured MCP endpoint and protocol headers

#### Scenario: MCP tool call
- **WHEN** a caller invokes an indexed MCP tool
- **THEN** the adapter SHALL send JSON-RPC over HTTP POST and support both `application/json` and `text/event-stream` responses

#### Scenario: Unsupported stdio MCP
- **WHEN** a plugin declares stdio MCP
- **THEN** the platform SHALL reject it during validation or installation in phase one

### Requirement: Skill Context capability
The system SHALL expose Skill Context capabilities as structured context assets, not as executable runtime tools.

#### Scenario: Read skill context
- **WHEN** a caller requests a Skill Context capability
- **THEN** the API SHALL return the skill name, description, usage guidance, and referenced context content

#### Scenario: Skill execution request
- **WHEN** a caller attempts to execute a Skill Context capability as a remote tool
- **THEN** the platform SHALL reject the request with a capability type error
