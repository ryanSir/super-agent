## ADDED Requirements

### Requirement: Plugin management console
The system SHALL provide an Admin Console for managing Registry plugins and workspace installations.

#### Scenario: List Registry plugins
- **WHEN** an admin opens the plugin marketplace or registry page
- **THEN** the console SHALL display plugin name, version, publisher, capability types, publish status, and install state

#### Scenario: View plugin details
- **WHEN** an admin opens a plugin detail page
- **THEN** the console SHALL display manifest metadata, versions, capabilities, required configuration, credential placeholders, and package checksum

### Requirement: Installation and enablement operations
The Admin Console SHALL call backend APIs to install, enable, disable, and bind plugins.

#### Scenario: Install from detail page
- **WHEN** an admin clicks install for a Registry plugin version
- **THEN** the console SHALL call Plugin Manager and refresh install state after success

#### Scenario: Enable failure
- **WHEN** enabling a plugin fails because required configuration is missing
- **THEN** the console SHALL show the missing configuration fields and SHALL NOT display the plugin as enabled

### Requirement: Frontend production boundaries
The Admin Console SHALL be implemented as a management workspace, not as a marketing page.

#### Scenario: First screen
- **WHEN** the console loads
- **THEN** the first screen SHALL be a usable plugin operations view with filters, state, and actions

#### Scenario: API unavailable
- **WHEN** backend APIs are unavailable or timeout
- **THEN** the console SHALL show an actionable error state without losing the current navigation context
