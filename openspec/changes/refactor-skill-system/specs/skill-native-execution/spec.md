## ADDED Requirements

### Requirement: Native Skill 通过 load_skill 按需加载

当主 Agent 判断用户任务匹配某个 native skill 时，系统 SHALL 通过框架内置的 `load_skill(name)` 工具加载完整 SKILL.md 内容到 Agent 上下文。

#### Scenario: 成功加载 native skill
- **WHEN** Agent 调用 `load_skill("api-design")`，且该 skill 的 `execution: native`
- **THEN** 返回完整 SKILL.md 内容（frontmatter + markdown 指引），Agent 可据此使用 Base Tool 执行

#### Scenario: 加载不存在的 skill
- **WHEN** Agent 调用 `load_skill("nonexistent")`
- **THEN** 返回错误信息，Agent 可调用 `list_skills()` 重新选择

### Requirement: Native Skill 可调用所有 Base Tool 和 MCP Tool

execution 为 native 的 Skill，主 Agent 在读取 SKILL.md 指引后 SHALL 能自由调用任意已注册的 Base Tool（web_search、rag_query、emit_chart 等）和 MCP Tool 来完成任务。

#### Scenario: Native skill 调用 web_search
- **WHEN** Agent 加载了 native skill "patent-analysis"，SKILL.md 指引中要求先搜索专利信息
- **THEN** Agent 调用 `baidu_search(query="专利号 CN202X...")` 获取结果，继续按 SKILL.md 指引处理

#### Scenario: Native skill 调用 MCP Tool
- **WHEN** Agent 加载了 native skill，SKILL.md 指引中要求调用某个 MCP 工具
- **THEN** Agent 可直接调用已注册的 MCP toolset 中的工具

#### Scenario: Native skill 多工具协同
- **WHEN** Agent 加载了 native skill，SKILL.md 指引包含多步骤流程（搜索 → RAG → 图表）
- **THEN** Agent 按指引依次调用 `baidu_search` → `rag_query` → `emit_chart`，中间可根据结果做判断和分支

### Requirement: Native Skill 通过 read_skill_resource 按需加载资源

Agent 在执行 native skill 过程中，SHALL 能通过 `read_skill_resource(name, path)` 按需读取 skill 目录下的模板、参考文档等资源文件。

#### Scenario: 读取模板文件
- **WHEN** Agent 执行 native skill，SKILL.md 指引要求使用 `templates/report.md` 模板
- **THEN** Agent 调用 `read_skill_resource("skill-name", "templates/report.md")` 获取模板内容

#### Scenario: 路径穿越防护
- **WHEN** Agent 调用 `read_skill_resource("skill-name", "../other-skill/SKILL.md")`
- **THEN** 系统 MUST 拒绝请求，返回路径安全错误

#### Scenario: 读取不存在的资源
- **WHEN** Agent 调用 `read_skill_resource("skill-name", "nonexistent.md")`
- **THEN** 返回文件不存在错误，Agent 可继续执行其他步骤

### Requirement: Native Skill 禁止调用 execute_skill

execution 为 native 的 Skill MUST NOT 通过 `execute_skill` 工具执行。系统 prompt 中 SHALL 明确引导 Agent 对 native skill 使用 `load_skill` → Base Tool 流程。

#### Scenario: Agent 尝试对 native skill 调用 execute_skill
- **WHEN** Agent 调用 `execute_skill("api-design", params)`，且该 skill 的 `execution: native`
- **THEN** 返回错误：`"技能 'api-design' 为 native 模式，请使用 load_skill 加载后直接执行"`

#### Scenario: 超时处理
- **WHEN** Agent 执行 native skill 过程中，某个 Base Tool 调用超时
- **THEN** Agent 按正常工具错误处理流程重试或跳过，不影响 skill 整体流程
