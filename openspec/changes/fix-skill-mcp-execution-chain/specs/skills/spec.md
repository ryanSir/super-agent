## MODIFIED Requirements

### Requirement: execute_skill 工具签名统一
`execute_skill` 工具在 main agent 和 direct agent 中 SHALL 使用相同的参数签名：`skill_name: str` + `params: Dict[str, Any]`，不得使用 `args: List[str]`。

#### Scenario: main agent 调用 Skill
- **WHEN** main agent 调用 `execute_skill(skill_name="baidu-search", params={"query": "xxx"})`
- **THEN** 系统 SHALL 正确构建 `SandboxTask` 并传入沙箱执行，不抛出 `NameError`

#### Scenario: direct agent 调用 Skill
- **WHEN** direct agent 调用 `execute_skill(skill_name="paper-search", params={"query": "yyy"})`
- **THEN** 系统 SHALL 使用与 main agent 相同的执行路径，返回相同结构的结果

#### Scenario: Skill 未注册
- **WHEN** 调用 `execute_skill` 时 `skill_name` 在 registry 中不存在
- **THEN** 系统 SHALL 返回 `{"success": false, "stderr": "Skill '...' 未注册", "exit_code": 1}`，不抛出异常

## ADDED Requirements

### Requirement: direct agent 支持渐进式 Skill 加载
direct agent SHALL 注册 `search_skills` 工具，使其能够在 system prompt 摘要命中后按需获取 Skill 完整定义。

#### Scenario: direct agent 检索 Skill
- **WHEN** direct agent 调用 `search_skills(query="搜索")`
- **THEN** 系统 SHALL 返回名称或描述中包含该关键词的所有 Skill 的完整 `SkillInfo`

#### Scenario: 无匹配 Skill
- **WHEN** direct agent 调用 `search_skills(query="不存在的关键词")`
- **THEN** 系统 SHALL 返回空列表，不抛出异常
