## ADDED Requirements

### Requirement: Runtime Host Lifecycle

The POC SHALL record runtime host lifecycle state for installed plugins.

#### Scenario: Start runtime

- **WHEN** the user starts runtime for an installed plugin
- **THEN** the runtime record SHALL become `running`
- **AND** stdio MCP entries SHALL be registered as adapter metadata

#### Scenario: Stop runtime

- **WHEN** the user stops runtime
- **THEN** the runtime record SHALL become `stopped`
