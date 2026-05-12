## ADDED Requirements

### Requirement: Plugin manifest validation

The system SHALL validate a plugin directory containing `plugin.yaml` before packaging or publishing.

#### Scenario: Valid manifest passes validation
- **WHEN** a plugin directory contains a valid `plugin.yaml` with required identity, capabilities, auth, permissions and runtime fields
- **THEN** validation succeeds and returns the parsed manifest summary

#### Scenario: Missing required field fails validation
- **WHEN** `plugin.yaml` is missing a required field such as `id`, `name`, `version` or `capabilities`
- **THEN** validation fails with a field-level error message

#### Scenario: Invalid path reference fails validation
- **WHEN** a capability references a child file through `path`, `spec` or `credential_schema` and the target file does not exist
- **THEN** validation fails and reports the missing path

#### Scenario: Invalid version fails validation
- **WHEN** `version` is not a semantic version in `MAJOR.MINOR.PATCH` form
- **THEN** validation fails and reports the version format error

### Requirement: Plugin package creation

The system SHALL create a deterministic zip package for a validated plugin directory.

#### Scenario: Package command creates zip artifact
- **WHEN** `plugin package` runs on a valid plugin directory
- **THEN** the system creates a zip file containing `plugin.yaml`, referenced child files, `package.json` and `checksums.json`

#### Scenario: Package command rejects invalid plugin
- **WHEN** `plugin package` runs on an invalid plugin directory
- **THEN** no package is created and validation errors are returned

#### Scenario: Package excludes generated files
- **WHEN** a plugin directory contains generated caches or local registry output
- **THEN** package creation excludes `__pycache__`, `.DS_Store`, `.plugin-registry` and package output files

### Requirement: Local registry publishing

The system SHALL publish a plugin package to a local file-based Registry.

#### Scenario: Publish stores package version
- **WHEN** `plugin publish` runs with a valid package
- **THEN** the Registry stores the package under plugin id and version and updates `index.json`

#### Scenario: Duplicate publish without force fails
- **WHEN** the same plugin id and version already exists in the Registry and publish runs without force
- **THEN** publish fails without overwriting existing package files

#### Scenario: Registry index lists published plugin
- **WHEN** a plugin package is published successfully
- **THEN** `index.json` includes plugin id, version, name, description, checksum and package path

### Requirement: CLI workflow

The system SHALL provide a CLI for validating, packaging and publishing plugins.

#### Scenario: Validate command exits successfully
- **WHEN** a user runs `python -m plugin_poc.cli validate <plugin_dir>` for a valid plugin
- **THEN** the command exits with status code 0

#### Scenario: Package command exits successfully
- **WHEN** a user runs `python -m plugin_poc.cli package <plugin_dir>`
- **THEN** the command exits with status code 0 and prints the package path

#### Scenario: Publish command exits successfully
- **WHEN** a user runs `python -m plugin_poc.cli publish <plugin_dir> --registry <registry_dir>`
- **THEN** the command packages the plugin, publishes it to the registry and prints the registry entry

### Requirement: Failure and timeout boundaries

The system SHALL avoid long-running runtime behavior in Phase 1 and fail fast for local file validation errors.

#### Scenario: File operation error fails fast
- **WHEN** the plugin directory is unreadable or the package output path cannot be written
- **THEN** the command fails with a clear error instead of blocking

#### Scenario: No runtime execution occurs
- **WHEN** validate, package or publish commands run
- **THEN** the system does not start plugin runtime processes or invoke external network services
