## ADDED Requirements

### Requirement: Plugin Registry version storage
The system SHALL store plugin package metadata and immutable version records in a Registry service.

#### Scenario: New version registered
- **WHEN** a package with a new plugin id and version is published
- **THEN** Registry SHALL persist manifest metadata, capability summary, checksum, created time, and package location

#### Scenario: Duplicate version rejected
- **WHEN** a package with an existing plugin id and version is published with different checksum
- **THEN** Registry SHALL reject the publish request and preserve the existing version record

### Requirement: Workspace plugin installation
The system SHALL allow Plugin Manager to install a Registry plugin version into a workspace.

#### Scenario: Install plugin
- **WHEN** an admin installs a plugin version into a workspace
- **THEN** Plugin Manager SHALL create a workspace installation record with disabled default state unless configured otherwise

#### Scenario: Install missing version
- **WHEN** an admin installs a plugin version that Registry cannot find
- **THEN** Plugin Manager SHALL return a not found error and SHALL NOT create an installation record

### Requirement: Workspace and agent enablement
The system SHALL manage plugin enablement separately from package registration.

#### Scenario: Enable for workspace
- **WHEN** an installed plugin is enabled for a workspace
- **THEN** Plugin Manager SHALL mark the installation enabled and generate or refresh the workspace Capability Index

#### Scenario: Enable for agent binding
- **WHEN** an installed plugin is bound to an agent
- **THEN** Plugin Manager SHALL record the binding and include applicable capabilities in that agent's Capability Index

#### Scenario: Disable plugin
- **WHEN** an installed plugin is disabled
- **THEN** Plugin Manager SHALL remove its capabilities from active indexes while preserving installation history

### Requirement: Capability Index generation
The system SHALL generate a queryable Capability Index from enabled plugin installations.

#### Scenario: Query workspace capabilities
- **WHEN** a caller requests capabilities for a workspace
- **THEN** the index SHALL return enabled capabilities grouped by type, plugin id, version, and invocation metadata

#### Scenario: Concurrent enable updates
- **WHEN** two enable or disable operations occur concurrently for the same workspace and plugin
- **THEN** the index SHALL end in a consistent state matching the last accepted installation state
