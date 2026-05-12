## Design

Skill capabilities remain normal capability index entries, scoped by workspace and agent.

At Agent runtime:

1. Agent asks for enabled skills by workspace and agent.
2. Skill runtime filters capability index entries with `type = skill`.
3. Each skill capability resolves to the installed plugin source file.
4. Runtime parses frontmatter from `SKILL.md`.
5. Runtime returns metadata or renders a combined Agent context block.

## Runtime Boundary

Skill Runtime is read-only:

- no external network calls
- no credentials
- no policy gate yet
- no audit record yet

This keeps skill discovery cheap and makes it suitable for prompt assembly before tool invocation.

## Later Enhancements

- task-aware skill selection
- skill ranking by description and capability metadata
- prompt placement policy
- audit records for selected skills
- skill dependency declarations
