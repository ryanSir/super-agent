## MODIFIED Requirements

### Requirement: SkillRegistry 接口
技能系统负责管理可插拔的外部能力包，支持自动发现、注册和执行。

SkillRegistry MUST 支持两阶段加载模式：
- 阶段 1（摘要模式）：`get_skill_summary()` 仅返回 Skill 名称和一句话描述列表，用于注入 system prompt
- 阶段 2（全量模式）：`search_skills(query)` 按关键词匹配，返回匹配 Skill 的完整定义（含 SKILL.md 全文）

```python
skill_registry = SkillRegistry()  # 全局单例

skill_registry.scan() -> int                          # 扫描 skill/ 目录，返回注册数量
skill_registry.get(name) -> SkillInfo                  # 获取单个 skill（完整信息）
skill_registry.list_skills() -> List                   # 列出所有 skill
skill_registry.list_names() -> List[str]               # 列出所有 skill 名称
skill_registry.get_skill_summary() -> str              # 生成摘要（仅名称+描述，注入 prompt）
skill_registry.search_skills(query: str) -> List[SkillInfo]  # 按关键词检索匹配 skill
skill_registry.register(info)                          # 手动注册
```

#### Scenario: 摘要模式注入 system prompt
- **WHEN** Orchestrator 构建 system prompt
- **THEN** 调用 `get_skill_summary()` 返回格式为 `Available skills: baidu-search (百度AI搜索), ai-ppt-generator (AI PPT生成), ...` 的紧凑文本

#### Scenario: 按需检索完整定义
- **WHEN** Agent 调用 `search_skills("ppt")`
- **THEN** 返回名称或描述中包含 "ppt" 的所有 Skill 的完整 SkillInfo（含 doc_content）

#### Scenario: 检索无匹配
- **WHEN** Agent 调用 `search_skills("nonexistent")`
- **THEN** 返回空列表

#### Scenario: 摘要 token 控制
- **WHEN** 注册了 20 个 Skill
- **THEN** `get_skill_summary()` 返回的文本 MUST 不超过 500 token（约 2000 字符）

### Requirement: 技能摘要注入方式
技能摘要 MUST 通过 `get_skill_summary()` 注入 Orchestrator 系统 Prompt。摘要仅包含 Skill 名称和一句话描述，不包含完整 SKILL.md 内容。Agent 需要完整定义时 MUST 通过 `search_skills` 工具按需获取。

#### Scenario: 对比全量注入的 token 节省
- **WHEN** 系统注册了 4 个 Skill，每个 SKILL.md 平均 500 token
- **THEN** 摘要模式注入约 100 token，相比全量注入（2000 token）节省约 95%

#### Scenario: 新 Skill 注册后摘要自动更新
- **WHEN** 通过 `register()` 动态注册新 Skill
- **THEN** 下次调用 `get_skill_summary()` MUST 包含新 Skill 的摘要
