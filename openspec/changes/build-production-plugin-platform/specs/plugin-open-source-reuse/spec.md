## ADDED Requirements

### Requirement: Module-level open source evaluation
The system SHALL evaluate open-source frameworks per module instead of replacing the entire platform with one framework.

#### Scenario: Framework assessment
- **WHEN** a module design references an open-source project
- **THEN** the assessment SHALL classify it as direct reuse, design reference, or not adopted, with rationale

#### Scenario: Production dependency acceptance
- **WHEN** a direct dependency is proposed
- **THEN** the assessment SHALL cover license, maintenance activity, integration cost, security posture, and replacement strategy

### Requirement: Required reference areas
The system SHALL maintain deep-dive notes for core open-source references relevant to the Plugin platform.

#### Scenario: Manifest and marketplace reference
- **WHEN** manifest, package layout, or marketplace design is changed
- **THEN** the design SHALL reference Codex Plugins and Dify plugin design where applicable

#### Scenario: Credential reference
- **WHEN** credential schema or credential configuration UI is changed
- **THEN** the design SHALL reference n8n credential concepts while preserving company secret-system integration boundaries

#### Scenario: MCP transport reference
- **WHEN** MCP runtime behavior is changed
- **THEN** the design SHALL reference MCP Streamable HTTP specification and Open WebUI's Streamable HTTP-only product model
