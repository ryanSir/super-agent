## ADDED Requirements

### Requirement: SkillRegistry 支持动态注册后立即生效
`SkillRegistry.register()` SHALL 在调用后立即更新内存注册表，使后续 `search_skills` 和 `get_skill_summary` 调用能感知新注册的技能。

#### Scenario: 动态注册后摘要更新
- **WHEN** 调用 `skill_registry.register(new_skill_info)`
- **THEN** 下次调用 `get_skill_summary()` MUST 包含新技能的名称和描述

#### Scenario: 动态注册后可检索
- **WHEN** 调用 `skill_registry.register(new_skill_info)`，技能名为 `"new-skill"`
- **THEN** 调用 `search_skills("new-skill")` MUST 返回该技能的完整 `SkillInfo`

### Requirement: SkillCreateRequest 数据模型
系统 SHALL 定义 `SkillCreateRequest` Pydantic 模型，用于技能创建请求的参数校验。

#### Scenario: 合法请求通过校验
- **WHEN** 构造 `SkillCreateRequest(name="my-skill", description="描述")`
- **THEN** 对象创建成功，`script_name` 默认为 `"main.py"`，`overwrite` 默认为 `False`

#### Scenario: 非法名称被拒绝
- **WHEN** 构造 `SkillCreateRequest(name="My Skill")`
- **THEN** Pydantic 抛出 `ValidationError`，错误字段为 `name`
