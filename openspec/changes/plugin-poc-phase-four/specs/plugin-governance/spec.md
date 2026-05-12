## ADDED Requirements

### Requirement: Credential configuration

The system SHALL configure credentials for an installed plugin within a workspace.

#### Scenario: Configure credential with required fields
- **WHEN** a user configures credential values satisfying the plugin credential schema
- **THEN** the system stores the credential and redacts secret values in list output

#### Scenario: Configure credential missing required field
- **WHEN** a user configures credential values missing a required field
- **THEN** the system fails with a credential validation error

### Requirement: Policy checks before invocation

The system SHALL run policy checks before invoking a tool capability.

#### Scenario: Invoke without required credential
- **WHEN** a plugin declares auth type other than `none` and no credential is configured
- **THEN** invocation fails with error code `missing_credential`

#### Scenario: Invoke sensitive action without confirmation
- **WHEN** a tool name is listed in `permissions.sensitive_actions` and confirmation is not provided
- **THEN** invocation fails with error code `sensitive_action_requires_confirmation`

#### Scenario: Invoke sensitive action with confirmation
- **WHEN** credential exists and confirmation is provided for a sensitive action
- **THEN** invocation proceeds to the runtime

### Requirement: Audit log

The system SHALL write an audit record for each invocation attempt.

#### Scenario: Audit successful invocation
- **WHEN** invocation succeeds
- **THEN** audit log records success, capability id, workspace, agent and user

#### Scenario: Audit failed invocation
- **WHEN** invocation fails due to policy or validation
- **THEN** audit log records failure and error code

### Requirement: Governance CLI

The system SHALL provide CLI commands for credential and audit operations.

#### Scenario: Configure credential through CLI
- **WHEN** user runs `configure-credential` with JSON values
- **THEN** command exits successfully and stores the credential

#### Scenario: List audit through CLI
- **WHEN** user runs `list-audit`
- **THEN** command prints audit records

