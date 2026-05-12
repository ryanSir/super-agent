## ADDED Requirements

### Requirement: Skill File Parsing

The POC SHALL parse plugin `SKILL.md` files with optional YAML frontmatter.

#### Scenario: Parse skill metadata

- **WHEN** a skill file starts with YAML frontmatter
- **THEN** the runtime SHALL return metadata such as `name` and `description`
- **AND** return the remaining markdown body as content

### Requirement: Enabled Skill Listing

The POC SHALL list skills enabled for a workspace and agent.

#### Scenario: List enabled plugin skills

- **GIVEN** a plugin with a skill capability is installed and enabled
- **WHEN** the user runs `list-skills`
- **THEN** the CLI SHALL return the skill capability id, plugin id, version, name, description and source path

### Requirement: Agent Skill Context Rendering

The POC SHALL render enabled plugin skills into an Agent-ready context block.

#### Scenario: Render skill context

- **GIVEN** one or more plugin skills are enabled for a workspace and agent
- **WHEN** the user runs `render-skill-context`
- **THEN** the CLI SHALL return a text context containing skill names, plugin versions, descriptions and instructions
