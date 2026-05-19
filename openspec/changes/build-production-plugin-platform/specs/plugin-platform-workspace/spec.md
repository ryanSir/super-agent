## ADDED Requirements

### Requirement: Independent plugin platform workspace
The system SHALL implement production plugin platform code under `plugin-platform/` without modifying current Agent runtime source directories.

#### Scenario: Agent source isolation
- **WHEN** plugin platform backend, CLI, frontend, examples, or tests are added
- **THEN** they SHALL be placed under `plugin-platform/` or `doc-plugin/` planning documents

#### Scenario: Future migration readiness
- **WHEN** the platform workspace is reviewed for extraction
- **THEN** backend, admin frontend, CLI/SDK, examples, and tests SHALL have clear directory boundaries and no hard dependency on `src_deepagent`

### Requirement: Deployment unit oriented structure
The system SHALL organize plugin platform modules according to future deployment responsibilities.

#### Scenario: Backend service location
- **WHEN** backend APIs or domain services are implemented
- **THEN** they SHALL live under `plugin-platform/services/`

#### Scenario: Admin console location
- **WHEN** management frontend code is implemented
- **THEN** it SHALL live under `plugin-platform/admin-console/`

#### Scenario: Developer tooling location
- **WHEN** validate, package, or publish tooling is implemented
- **THEN** it SHALL live under `plugin-platform/developer-tools/`
