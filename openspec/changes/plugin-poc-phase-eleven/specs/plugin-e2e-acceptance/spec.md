## ADDED Requirements

### Requirement: Local E2E Acceptance

The POC SHALL provide a local command that validates the plugin lifecycle from publish to invocation.

#### Scenario: Run local E2E

- **WHEN** the user runs `run-e2e`
- **THEN** the CLI SHALL publish, install, enable and configure the demo plugin
- **AND** start runtime host state
- **AND** invoke a tool and data source capability
- **AND** render skill context
- **AND** return `status: ok` when all required checks pass
