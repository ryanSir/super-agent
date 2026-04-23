---
name: awesome-design-md
description: Use when the user wants to add, install, or apply a DESIGN.md style from VoltAgent awesome-design-md/getdesign.md to the current project for Codex or another AI coding agent. Trigger on requests like "配置 awesome-design-md 到 codex", "安装 DESIGN.md", "用 vercel/claude/linear 风格", or "setup getdesign".
---

# Awesome Design MD

This skill installs a `DESIGN.md` file into the current project with the official `getdesign` CLI.

## When to use

- The user wants Codex to follow a specific UI style through `DESIGN.md`
- The user references `awesome-design-md`, `getdesign.md`, or a style like `vercel`, `claude`, or `stripe`
- The user wants to list available design presets before choosing one

## Workflow

1. If the user asks what styles exist, run `bash scripts/install-design.sh --list`.
2. If the user names a style, run `bash scripts/install-design.sh <style>` from the project root.
3. If `DESIGN.md` already exists, do not overwrite it unless the user explicitly asks. The helper script refuses by default.
4. After install, treat `DESIGN.md` as the active UI design contract for future frontend work.

## Notes

- Available style slugs are in `references/designs.txt`.
- The installer uses `npx getdesign@latest add <style>`, so network access may require approval.
- If the user only asked to "configure" this for Codex, installing this skill is enough. A style can be added later on demand.
