## MODIFIED Requirements

### Requirement: Skill 版本管理
SkillRegistry SHALL 支持技能版本管理（semver），同一技能可注册多个版本。默认使用最新版本，支持指定版本调用。

#### Scenario: 多版本共存
- **WHEN** baidu-search 技能存在 v1.0.0 和 v2.0.0 两个版本
- **THEN** 默认调用 v2.0.0，execute_skill("baidu-search@1.0.0", ...) 可指定旧版本

#### Scenario: 版本兼容性
- **WHEN** 技能升级包含 breaking change（参数变更）
- **THEN** 系统 SHALL 保留旧版本可用，新版本的 SKILL.md 中 SHALL 声明 breaking_changes

### Requirement: Skill 市场发布与发现
SkillRegistry SHALL 扩展为支持市场功能：技能发布（上传+审核）、技能发现（搜索+分类+评分）、技能安装（下载+注册）。

#### Scenario: 技能发布
- **WHEN** 开发者提交技能包到市场
- **THEN** 系统 SHALL 校验 SKILL.md 格式、运行基础测试、通过后上架

#### Scenario: 技能搜索
- **WHEN** 用户在市场搜索 "数据分析"
- **THEN** 系统 SHALL 返回匹配技能列表，按安装量和评分排序
