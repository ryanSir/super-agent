## ADDED Requirements

### Requirement: SKILL.md frontmatter 支持 execution 字段

SKILL.md 的 YAML frontmatter SHALL 支持 `execution` 字段，取值为 `native` 或 `sandbox`，默认值为 `sandbox`。

#### Scenario: 显式声明 native 模式
- **WHEN** SKILL.md frontmatter 包含 `execution: native`
- **THEN** 系统将该 Skill 标记为 native 模式，Agent 通过 `load_skill` + Base Tool 执行

#### Scenario: 显式声明 sandbox 模式
- **WHEN** SKILL.md frontmatter 包含 `execution: sandbox`
- **THEN** 系统将该 Skill 标记为 sandbox 模式，Agent 通过 `execute_skill` 委托 Pi Agent 执行

#### Scenario: 未声明 execution 字段（向后兼容）
- **WHEN** SKILL.md frontmatter 不包含 `execution` 字段
- **THEN** 系统 MUST 默认为 `sandbox` 模式，行为与当前完全一致

#### Scenario: 无效的 execution 值
- **WHEN** SKILL.md frontmatter 包含 `execution: invalid_value`
- **THEN** 系统 MUST 记录警告日志，回退为 `sandbox` 模式

### Requirement: list_skills 返回 execution 模式信息

`list_skills()` 返回的技能摘要 SHALL 包含每个 Skill 的 execution 模式，以便 Agent 判断执行路径。

#### Scenario: 混合模式 skill 列表
- **WHEN** 系统注册了 native skill "api-design" 和 sandbox skill "data-processor"
- **THEN** `list_skills()` 返回结果中每个 skill 包含 `execution` 字段，Agent 可据此选择 `load_skill` 或 `execute_skill`

#### Scenario: 全部为 sandbox 模式
- **WHEN** 所有已注册 Skill 的 execution 均为 sandbox
- **THEN** `list_skills()` 正常返回，Agent 行为与重构前一致

### Requirement: 执行路径路由

系统 SHALL 根据 Skill 的 execution 模式自动路由到正确的执行路径。

#### Scenario: Native skill 执行路径
- **WHEN** Agent 选择了 execution 为 native 的 Skill
- **THEN** Agent 调用 `load_skill(name)` → 读取 SKILL.md 指引 → 使用 Base Tool / MCP Tool 执行

#### Scenario: Sandbox skill 执行路径
- **WHEN** Agent 选择了 execution 为 sandbox 的 Skill
- **THEN** Agent 调用 `execute_skill(name, params)` → Pi Agent 在沙箱中执行脚本

#### Scenario: Sandbox skill 可选预加载
- **WHEN** Agent 选择了 execution 为 sandbox 的 Skill，且需要理解上下文
- **THEN** Agent 可先调用 `load_skill(name)` 了解 Skill 用途和参数格式，再调用 `execute_skill`

### Requirement: System Prompt 中的路由引导

system prompt 中 SHALL 包含明确的执行路径引导，告知 Agent 如何根据 execution 模式选择正确的工具调用序列。

#### Scenario: Prompt 引导内容
- **WHEN** 系统构建 system prompt
- **THEN** skill 相关段落 MUST 包含：native skill 使用 `load_skill` → Base Tool 流程，sandbox skill 使用 `execute_skill` 流程

#### Scenario: 无可用 skill 时
- **WHEN** 系统无已注册 Skill
- **THEN** system prompt 中 MUST NOT 包含 skill 路由引导段落
