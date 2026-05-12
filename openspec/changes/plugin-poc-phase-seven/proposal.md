## Why

The POC already indexes skill capabilities, but Agent Runtime still has no direct way to consume plugin skill instructions. Phase 7 closes that gap by loading `SKILL.md` files from enabled plugins and rendering them into an Agent-ready context block.

## What Changes

- Parse plugin `SKILL.md` files with YAML frontmatter.
- Add skill metadata to the capability index.
- Add CLI commands to list enabled skills and render skill context.
- Add tests for parsing, listing and context rendering.

## Scope

This phase only exposes skill content to the Agent layer. It does not implement final prompt injection strategy, skill ranking, or task-based skill selection.
