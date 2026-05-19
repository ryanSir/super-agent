## ADDED Requirements

### Requirement: Plugin manifest validation
The system SHALL validate plugin packages against a versioned `plugin.yaml` schema before packaging or publishing.

#### Scenario: Valid plugin
- **WHEN** a plugin directory contains a valid manifest and referenced capability files
- **THEN** validation SHALL return success with normalized plugin metadata and capability summary

#### Scenario: Missing referenced file
- **WHEN** `plugin.yaml` references a skill, OpenAPI, MCP, credential, or asset file that does not exist
- **THEN** validation SHALL fail with the missing path and the manifest field that referenced it

#### Scenario: Unsupported MCP transport
- **WHEN** an MCP capability declares `stdio` transport in phase one
- **THEN** validation SHALL fail and explain that only Streamable HTTP MCP is supported in this phase

### Requirement: Plugin package creation
The system SHALL create deterministic plugin package artifacts from validated plugin directories.

#### Scenario: Package success
- **WHEN** a valid plugin directory is packaged
- **THEN** the output SHALL include package metadata, manifest snapshot, content checksum, and all referenced files

#### Scenario: Package validation failure
- **WHEN** a plugin directory fails validation
- **THEN** packaging SHALL stop and no publishable artifact SHALL be produced

### Requirement: Plugin publish command
The system SHALL support publishing a validated package to the Registry API.

#### Scenario: Publish success
- **WHEN** a developer publishes a valid package to a reachable Registry
- **THEN** the Registry SHALL store the package version and return plugin id, version, checksum, and status

#### Scenario: Publish timeout
- **WHEN** the Registry does not respond within the configured timeout
- **THEN** the publish command SHALL fail with a retryable error and SHALL NOT mark the package as published locally
