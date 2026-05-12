## ADDED Requirements

### Requirement: Tool capability invocation

The system SHALL invoke an enabled tool capability through a unified gateway.

#### Scenario: Invoke enabled tool capability
- **WHEN** a user invokes `company.slack-demo.tool.send_message` with required input for the matching workspace and agent
- **THEN** the system returns a successful invocation result with runtime `local_mock_tool`

#### Scenario: Invoke missing capability
- **WHEN** a user invokes a capability id that is not present for the workspace and agent
- **THEN** the system returns a failed invocation result with error code `capability_not_found`

#### Scenario: Invoke unsupported capability type
- **WHEN** a user invokes a capability whose type is not `tool`
- **THEN** the system returns a failed invocation result with error code `unsupported_capability_type`

### Requirement: Tool input validation

The system SHALL validate required fields before invoking a tool capability.

#### Scenario: Missing required tool input
- **WHEN** a user invokes a tool capability without a required input field
- **THEN** the system returns a failed invocation result with error code `invalid_input`

#### Scenario: Valid required tool input
- **WHEN** a user invokes a tool capability with all required input fields
- **THEN** the system returns a successful invocation result

### Requirement: CLI invocation workflow

The system SHALL provide an `invoke` CLI command.

#### Scenario: CLI invoke succeeds
- **WHEN** a user runs `invoke` with a valid capability id, workspace, agent and JSON input
- **THEN** the command exits successfully and prints the invocation result

#### Scenario: CLI invoke handles invalid JSON
- **WHEN** a user runs `invoke` with invalid JSON input
- **THEN** the command exits with an error message

