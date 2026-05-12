## ADDED Requirements

### Requirement: Plugin installation from local registry

The system SHALL install a plugin package from a local Registry into a local state directory.

#### Scenario: Install existing plugin version
- **WHEN** a user installs `company.slack-demo@1.0.0` from a Registry containing that version
- **THEN** the system copies package files into state and records the plugin as installed

#### Scenario: Install missing plugin version
- **WHEN** a user installs a plugin id or version that does not exist in the Registry
- **THEN** installation fails with a clear error

### Requirement: Plugin enable and disable

The system SHALL enable or disable an installed plugin for a workspace and agent.

#### Scenario: Enable installed plugin
- **WHEN** a user enables an installed plugin for `workspace=ws_001` and `agent=agent_001`
- **THEN** the system records the binding and writes capabilities to the Capability Index

#### Scenario: Enable missing plugin
- **WHEN** a user enables a plugin version that is not installed
- **THEN** enable fails with a clear error

#### Scenario: Disable enabled plugin
- **WHEN** a user disables an enabled plugin for a workspace and agent
- **THEN** the system removes matching capabilities from the Capability Index

### Requirement: Capability index and resolver

The system SHALL expose enabled plugin capabilities through a queryable local Capability Index.

#### Scenario: List capabilities for enabled plugin
- **WHEN** a plugin with tools, skills, openapi, mcp and data_sources is enabled
- **THEN** list-capabilities returns all declared capabilities for the workspace and agent

#### Scenario: List capabilities after disable
- **WHEN** an enabled plugin is disabled
- **THEN** list-capabilities no longer returns that plugin's capabilities

#### Scenario: Query different agent
- **WHEN** a plugin is enabled for one agent but capabilities are listed for another agent
- **THEN** those capabilities are not returned

### Requirement: CLI installation workflow

The system SHALL provide CLI commands for install, enable, disable, uninstall, list-installed and list-capabilities.

#### Scenario: CLI install and enable workflow
- **WHEN** a user publishes a plugin, installs it, enables it and lists capabilities
- **THEN** each command exits successfully and list-capabilities returns enabled capabilities

#### Scenario: CLI uninstall removes plugin state
- **WHEN** a user uninstalls a plugin version
- **THEN** installed state and related enabled capabilities are removed

