## ADDED Requirements

### Requirement: OpenAPI capability invocation

The system SHALL invoke an enabled OpenAPI capability through the unified gateway using mock transport.

#### Scenario: Invoke OpenAPI operation
- **WHEN** a user invokes an OpenAPI capability with a valid `operation_id`
- **THEN** the system returns a successful invocation result with runtime `mock_openapi`

#### Scenario: Invoke OpenAPI missing operation_id
- **WHEN** a user invokes an OpenAPI capability without `operation_id`
- **THEN** invocation fails with error code `invalid_input`

#### Scenario: Invoke unknown OpenAPI operation
- **WHEN** a user invokes an OpenAPI capability with an unknown `operation_id`
- **THEN** invocation fails with error code `operation_not_found`

### Requirement: OpenAPI invocation audit

The system SHALL write audit records for OpenAPI invocation attempts.

#### Scenario: Audit successful OpenAPI invocation
- **WHEN** OpenAPI invocation succeeds
- **THEN** audit log records success and capability id

#### Scenario: Audit failed OpenAPI invocation
- **WHEN** OpenAPI invocation fails
- **THEN** audit log records failure and error code

