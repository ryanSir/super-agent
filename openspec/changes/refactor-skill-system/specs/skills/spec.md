## MODIFIED Requirements

### Requirement: SkillRegistry 接口

技能系统负责管理可插拔的外部能力包，支持自动发现、注册和执行。

SkillRegistry 精简为动态注册后端，文件系统发现和三阶段加载 SHALL 委托给 pydantic-deep 框架的 `SkillsToolset`。

SkillRegistry MUST 保留以下接口用于动态注册场景：

```python
skill_registry = SkillRegistry()  # 全局单例

skill_registry.register(info)                          # 手动注册（create_skill 后立即生效）
skill_registry.get(name) -> SkillInfo                  # 获取单个 skill
skill_registry.list_names() -> List[str]               # 列出所有 skill 名称
```

以下接口 SHALL 标记为 deprecated 并在后续版本移除，由 SkillsToolset 替代：

```python
# DEPRECATED — 由 SkillsToolset.list_skills() 替代
skill_registry.scan() -> int
skill_registry.get_skill_summary() -> str
skill_registry.search_skills(query) -> List[SkillInfo]
skill_registry.list_skills() -> List
```

#### Scenario: 动态注册后立即可用
- **WHEN** 通过 `create_skill` 工具创建新 Skill 后调用 `register(info)`
- **THEN** 新 Skill 立即可通过 `get(name)` 获取，且下次 `list_skills()` 调用时可见

#### Scenario: 框架 SkillsToolset 发现文件系统 Skill
- **WHEN** Agent 启动时配置了 `skill_directories=[{"path": "./skill", "recursive": True}]`
- **THEN** 框架自动扫描 `skill/` 目录，`list_skills()` 返回所有已发现的 Skill 摘要

### Requirement: SkillMetadata 数据模型

```python
class SkillMetadata(BaseModel):
    name: str                              # 小写字母 + 连字符
    description: str                       # 一句话描述
    path: str                              # 技能目录路径
    execution: Literal["native", "sandbox"] = "sandbox"  # 执行模式
```

#### Scenario: 解析包含 execution 字段的 frontmatter
- **WHEN** SKILL.md frontmatter 为 `name: api-design\ndescription: API 设计\nexecution: native`
- **THEN** 解析结果 `SkillMetadata.execution == "native"`

#### Scenario: 解析不包含 execution 字段的 frontmatter
- **WHEN** SKILL.md frontmatter 为 `name: data-processor\ndescription: 数据处理`
- **THEN** 解析结果 `SkillMetadata.execution == "sandbox"`（默认值）

### Requirement: execute_skill 仅限 sandbox 模式

`execute_skill` base tool SHALL 仅接受 `execution: sandbox` 的 Skill。对 native Skill 的调用 MUST 返回错误引导。

#### Scenario: 正常执行 sandbox skill
- **WHEN** Agent 调用 `execute_skill("data-processor", params)`，且该 skill `execution: sandbox`
- **THEN** 正常走沙箱执行流程，Pi Agent 执行脚本并返回结果

#### Scenario: 拒绝执行 native skill
- **WHEN** Agent 调用 `execute_skill("api-design", params)`，且该 skill `execution: native`
- **THEN** 返回 `{"success": False, "error": "技能 'api-design' 为 native 模式，请使用 load_skill 加载后直接执行"}`

#### Scenario: Skill 不存在
- **WHEN** Agent 调用 `execute_skill("nonexistent", params)`
- **THEN** 返回 `{"success": False, "error": "技能 'nonexistent' 未找到"}`

### Requirement: Context Builder 不再手动拼接 skill_summary

`build_dynamic_instructions()` 中的 `<skill_system>` 段 SHALL 移除。Skill 摘要由框架 `SkillsToolset` 自动管理，不再需要手动注入 system prompt。

#### Scenario: 启用 SkillsToolset 后的 prompt 构建
- **WHEN** 调用 `build_dynamic_instructions(skill_summary="...")`
- **THEN** 函数 MUST 忽略 `skill_summary` 参数，不再拼接 `<skill_system>` 段

#### Scenario: 框架自动注入 skill 工具描述
- **WHEN** Agent 创建时 `include_skills=True`
- **THEN** 框架自动将 `list_skills` / `load_skill` / `read_skill_resource` 工具注入 Agent，工具描述中包含可用 Skill 信息

### Requirement: Agent Factory 启用 SkillsToolset

`create_orchestrator_agent()` SHALL 配置 `include_skills=True` 和 `skill_directories` 参数。

#### Scenario: 正常启动
- **WHEN** 调用 `create_orchestrator_agent(plan, sub_agent_configs)`
- **THEN** 创建的 Agent 包含 `list_skills` / `load_skill` / `read_skill_resource` 三个框架工具

#### Scenario: skill 目录不存在
- **WHEN** 配置的 `skill_directories` 路径不存在
- **THEN** Agent 正常创建，`list_skills()` 返回空列表，不影响其他功能

#### Scenario: 与 MCP toolset 共存
- **WHEN** Agent 同时配置了 `include_skills=True` 和 MCP toolsets
- **THEN** Agent 可同时使用 skill 工具和 MCP 工具，无冲突

## REMOVED Requirements

### Requirement: search_skills base tool
**Reason**: 由框架 `SkillsToolset` 的 `list_skills()` 替代。`list_skills` 返回所有 Skill 摘要，Agent 自行判断相关性，不再需要关键词搜索。
**Migration**: Agent 使用 `list_skills()` 浏览可用 Skill，使用 `load_skill(name)` 获取完整内容。

### Requirement: 摘要模式注入 system prompt
**Reason**: 不再通过 `get_skill_summary()` 手动拼接到 system prompt。框架 `SkillsToolset` 自动管理 Skill 发现，Agent 通过 `list_skills()` 工具按需获取。
**Migration**: 移除 `build_dynamic_instructions()` 中的 `<skill_system>` 段和 `skill_summary` 参数。
