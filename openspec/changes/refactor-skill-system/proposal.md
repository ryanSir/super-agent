## Why

当前 Skill 系统将所有技能统一扔进沙箱执行（Pi Agent 全权负责），导致 Skill 与 Base Tool 完全隔离 — 无法在 Skill 执行过程中调用 web_search、rag_query、MCP 工具等。同时，自研的 SkillRegistry 与 pydantic-deep 框架已内置的 SkillsToolset 功能高度重叠，维护成本高且无法跟随框架升级。

参考 DeerFlow 的实践验证：大部分 Skill 应作为"专家知识模板"由主 Agent 直接用 Base Tool 执行，仅需代码执行的场景才走沙箱。

## What Changes

- **替换 SkillRegistry**：用 pydantic-deep 框架内置的 `SkillsToolset`（`list_skills` / `load_skill` / `read_skill_resource`）替代自研的 `SkillRegistry`，复用框架的三阶段渐进式加载、缓存、路径安全机制
- **新增 Skill 执行模式分流**：在 SKILL.md frontmatter 中新增 `execution` 字段（`native` | `sandbox`），native 模式下主 Agent 读取 SKILL.md 后直接用 Base Tool 执行；sandbox 模式下委托 Pi Agent 执行脚本
- **重构 execute_skill**：当前的 `execute_skill` base tool 拆分为两条路径 — native skill 不再需要此工具（主 Agent 通过 `load_skill` 读取指引后自主执行），sandbox skill 保留 Pi Agent 执行但职责收窄为"脚本执行手臂"
- **删除冗余代码**：移除 `capabilities/skills/registry.py` 中与框架重叠的扫描、解析、缓存逻辑
- **更新 Context Builder**：`build_dynamic_instructions()` 中的 `<skill_system>` 段改为由 SkillsToolset 自动注入，不再手动拼接摘要

## Non-goals

- 不实现 Skill Evolution（动态学习/自动创建 Skill）— 后续独立迭代
- 不改变 Pi Agent 沙箱执行引擎本身的实现
- 不迁移现有 Skill 包的目录结构（SKILL.md + scripts/ + references/ 保持不变）
- 不修改前端 A2UI 组件

## Capabilities

### New Capabilities

- `skill-native-execution`: Native 模式 Skill 执行 — 主 Agent 读取 SKILL.md 后直接使用 Base Tool / MCP Tool 完成任务，不经过沙箱
- `skill-mode-routing`: Skill 执行模式路由 — 根据 SKILL.md frontmatter 中的 `execution` 字段决定走 native 还是 sandbox 路径

### Modified Capabilities

- `skills`: 替换 SkillRegistry 为 pydantic-deep SkillsToolset，更新三阶段加载机制、frontmatter schema、execute_skill 工具行为

## Impact

- **核心代码变更**：
  - `capabilities/skills/registry.py` — 大幅精简或删除，由 SkillsToolset 替代
  - `capabilities/skills/schema.py` — SkillMetadata 新增 `execution` 字段
  - `capabilities/base_tools.py` — `execute_skill` 重构为 sandbox-only，新增 native 路径
  - `context/builder.py` — 移除手动 skill_summary 拼接
  - `orchestrator/reasoning_engine.py` — `_resolve_resources()` 中 skill 加载方式变更
  - `orchestrator/agent_factory.py` — 注入 SkillsToolset
- **依赖变更**：需确认 `pydantic-deep` 版本支持 `SkillsToolset` API
- **现有 Skill 包**：需在 frontmatter 中补充 `execution: native | sandbox` 字段（默认 `sandbox` 保持向后兼容）
