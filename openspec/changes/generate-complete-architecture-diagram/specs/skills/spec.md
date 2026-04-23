## ADDED Requirements

### Requirement: Skills can produce project documentation artifacts
技能系统 SHALL 允许将技能作为项目文档交付工具使用，而不仅限于运行时工具调用。对于架构图场景，系统 MUST 支持通过 `fireworks-tech-graph` 生成项目内正式文档产物，并将产物保存到文档目录。

#### Scenario: Fireworks tech graph is used as documentation generator
- **WHEN** 用户请求生成项目技术架构图
- **THEN** 系统 MUST 允许使用 `fireworks-tech-graph` 生成 `doc-arch/` 下的正式 SVG/PNG 文档产物

#### Scenario: Skill output is persisted in repository
- **WHEN** 技能成功生成架构图
- **THEN** 输出 MUST 保存为仓库内文件，而不是仅作为临时会话结果存在

### Requirement: Skill-driven architecture diagrams use explicit style and source data
当技能用于生成项目技术架构图时，系统 MUST 同时保存结构化源数据和最终导出产物，并明确指定风格。对于本次能力，默认风格 MUST 为 Claude 官方风格。

#### Scenario: Structured source is preserved
- **WHEN** 通过 `fireworks-tech-graph` 生成架构图
- **THEN** 系统 MUST 保留对应的结构化 JSON 源文件，以支持后续迭代

#### Scenario: Style is fixed for consistency
- **WHEN** 项目技术架构图被重新生成
- **THEN** 系统 MUST 使用相同的 Claude 官方风格，避免每次输出风格漂移
