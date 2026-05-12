# Phase 7: Skill Runtime

Phase 7 makes plugin skills consumable by the Agent layer.

Earlier phases already registered `skill` entries in the Capability Index. This phase adds the missing runtime behavior:

- parse `SKILL.md` frontmatter
- expose enabled skill metadata
- optionally return skill content
- render all enabled plugin skills into an Agent context block

## Validate Existing Demo Plugin

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate plugin-poc/examples/slack-demo
```

## Publish, Install And Enable

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo \
  --registry /tmp/plugin-poc-registry \
  --force

PYTHONPATH=plugin-poc python -m plugin_poc.cli install company.slack-demo \
  --version 1.0.0 \
  --registry /tmp/plugin-poc-registry \
  --state /tmp/plugin-poc-state

PYTHONPATH=plugin-poc python -m plugin_poc.cli enable company.slack-demo \
  --version 1.0.0 \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

## List Enabled Skills

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-skills \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

Expected output contains:

```json
{
  "capability_id": "company.slack-demo.skill.summarize-channel",
  "name": "summarize-channel",
  "description": "Summarize recent channel messages."
}
```

To include the `SKILL.md` body:

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli list-skills \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001 \
  --include-content
```

## Render Agent Skill Context

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli render-skill-context \
  --state /tmp/plugin-poc-state \
  --workspace ws_001 \
  --agent agent_001
```

The `context` field is the text block that Agent Runtime can inject into its prompt or planning context.

## Current Boundary

This phase does not yet decide final prompt placement. It only provides the platform API needed by Agent Runtime:

- `list-skills` for discovery
- `render-skill-context` for prompt/context assembly

Later Agent integration can choose whether to inject all enabled skills, select by task, or let Capability Resolver rank skills.
