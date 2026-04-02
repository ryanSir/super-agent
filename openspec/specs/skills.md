# Skills 规格

## 职责

技能系统负责管理可插拔的外部能力包，支持自动发现、注册和执行。

## 核心文件

- `src/skills/registry.py` — 扫描 `skill/` 目录，解析 SKILL.md，维护全局注册表
- `src/skills/executor.py` — 技能执行（Agent 驱动 / 直接脚本）
- `src/skills/creator.py` — 技能创建与脚手架生成
- `src/skills/schema.py` — 技能数据模型

## 技能包目录结构

```
skill/<skill-name>/
├── SKILL.md          # 技能元数据（YAML frontmatter + 文档）
├── scripts/          # 可执行脚本（.py / .sh / .js / .ts）
└── references/       # 参考文档
```

## SKILL.md Frontmatter 格式

```yaml
---
name: skill-name          # 小写字母 + 连字符
description: 技能描述
---
```

## SkillRegistry 接口

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

## 已注册技能

| 技能名 | 目录 | 功能 |
|--------|------|------|
| baidu-search | `skill/baidu-search-1.1.3/` | 百度 AI 搜索 |
| ai-ppt-generator | `skill/ai-ppt-generator-1.1.4/` | AI PPT 生成 |
| ai-patent-trend-analysis | `skill/ai-patent-trend-analysis/` | 专利趋势分析 |
| paper-search | `skill/paper-search/` | 论文检索 |

## 关键约束

- 技能目录必须包含 `SKILL.md`，否则跳过
- 技能名称规范：小写字母 + 连字符，不含空格和特殊字符
- `scan()` 每次调用会清空并重新注册（`_skills.clear()`）
- 动态创建的技能通过 `register()` 手动注入，不依赖文件系统扫描
- 技能摘要通过 `get_skill_summary()` 注入 Orchestrator 系统 Prompt（仅名称+描述，不含完整 SKILL.md）
- Agent 需要完整定义时 MUST 通过 `search_skills` 工具按需获取

#### 技能摘要注入方式

技能摘要 MUST 通过 `get_skill_summary()` 注入 Orchestrator 系统 Prompt。摘要仅包含 Skill 名称和一句话描述，不包含完整 SKILL.md 内容。Agent 需要完整定义时 MUST 通过 `search_skills` 工具按需获取。

#### Scenario: 对比全量注入的 token 节省
- **WHEN** 系统注册了 4 个 Skill，每个 SKILL.md 平均 500 token
- **THEN** 摘要模式注入约 100 token，相比全量注入（2000 token）节省约 95%

#### Scenario: 新 Skill 注册后摘要自动更新
- **WHEN** 通过 `register()` 动态注册新 Skill
- **THEN** 下次调用 `get_skill_summary()` MUST 包含新 Skill 的摘要

## 数据模型

```python
class SkillMetadata(BaseModel):
    name: str
    description: str
    path: str

class SkillInfo(BaseModel):
    metadata: SkillMetadata
    scripts: List[str]      # scripts/ 下的脚本文件名
    references: List[str]   # references/ 下的文件名
    doc_content: str        # SKILL.md 完整内容

class SkillExecuteRequest(BaseModel):
    skill_name: str
    args: List[str]
```
