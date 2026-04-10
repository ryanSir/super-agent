## ADDED Requirements

### Requirement: SKILL.md 声明式加载
系统 SHALL 支持通过 SKILL.md frontmatter 声明技能元数据（name、description、version、triggers、params、scripts）。系统启动时 SHALL 自动扫描 skill/ 目录并注册所有合法技能。

#### Scenario: 正常加载
- **WHEN** skill/baidu-search/SKILL.md 存在且 frontmatter 格式正确
- **THEN** 系统 SHALL 解析并注册该技能，技能名称为 "baidu-search"

#### Scenario: frontmatter 格式错误
- **WHEN** SKILL.md 缺少必填字段（name 或 description）
- **THEN** 系统 SHALL 跳过该技能，记录 WARNING 日志，不影响其他技能加载

#### Scenario: 技能名称冲突
- **WHEN** 两个技能目录声明了相同的 name
- **THEN** 系统 SHALL 拒绝后加载的技能，记录 ERROR 日志

### Requirement: 触发匹配三通道
系统 SHALL 支持三种技能触发方式：关键词匹配（triggers 字段）、语义匹配（Embedding 相似度）、显式调用（用户指定技能名）。匹配优先级：显式调用 > 关键词 > 语义。

#### Scenario: 关键词触发
- **WHEN** 用户查询包含 "百度搜索" 且 baidu-search 技能的 triggers 包含 "百度搜索"
- **THEN** 系统 SHALL 匹配到 baidu-search 技能

#### Scenario: 语义触发
- **WHEN** 用户查询 "帮我在网上找一下" 且无关键词精确匹配
- **THEN** 系统 SHALL 通过语义相似度匹配到最相关的搜索类技能

#### Scenario: 显式调用
- **WHEN** Agent 调用 execute_skill("baidu-search", params)
- **THEN** 系统 SHALL 直接执行指定技能，跳过匹配流程

### Requirement: 三阶段渐进加载
系统 SHALL 实现技能的三阶段渐进加载：Stage 1（启动时扫描 → 摘要注入 prompt）、Stage 2（Agent 调 search_skills → 返回完整文档）、Stage 3（Agent 调 execute_skill → 注入脚本到沙箱执行）。

#### Scenario: Stage 1 摘要注入
- **WHEN** 系统启动完成
- **THEN** 所有已注册技能的名称+描述 SHALL 以紧凑摘要形式注入 System Prompt

#### Scenario: Stage 2 文档检索
- **WHEN** Agent 调用 search_skills("论文搜索")
- **THEN** 系统 SHALL 返回匹配技能的完整 doc_content（SKILL.md 正文部分）

#### Scenario: Stage 3 脚本执行
- **WHEN** Agent 调用 execute_skill("baidu-search", {"query": "AI论文"})
- **THEN** 系统 SHALL 读取技能脚本文件，注入沙箱，通过 Pi Agent 执行并返回结果

### Requirement: Skill 市场
系统 SHALL 支持技能的发布、发现、版本管理。技能发布 SHALL 包含版本号（semver）、变更日志、兼容性声明。

#### Scenario: 技能发布
- **WHEN** 开发者提交技能包（包含 SKILL.md + scripts/）
- **THEN** 系统 SHALL 校验格式、分配版本号、存入技能仓库

#### Scenario: 技能发现
- **WHEN** 用户搜索 "数据分析" 类技能
- **THEN** 系统 SHALL 返回匹配的技能列表，按相关性和评分排序

#### Scenario: 版本升级
- **WHEN** 技能发布新版本且存在 breaking change
- **THEN** 系统 SHALL 保留旧版本可用，新安装默认使用新版本
