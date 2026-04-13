## ADDED Requirements

### Requirement: Agent 可通过工具调用创建新技能包
系统 SHALL 提供 `create_skill` 工具函数，允许 Agent 在运行时创建符合规范的技能包目录结构，并自动注册到 `SkillRegistry`。

#### Scenario: 最小化创建（仅提供名称和描述）
- **WHEN** Agent 调用 `create_skill(name="my-skill", description="我的技能")`
- **THEN** 系统在 `skill/my-skill/` 下创建 `SKILL.md`、`scripts/main.py`，并返回 `SkillInfo`

#### Scenario: 完整创建（提供脚本内容）
- **WHEN** Agent 调用 `create_skill(name="my-skill", description="...", script_content="#!/usr/bin/env python3\n...")`
- **THEN** 系统将 `script_content` 写入 `skill/my-skill/scripts/main.py`，文件权限设为 0o755

#### Scenario: 自定义脚本文件名
- **WHEN** Agent 调用 `create_skill(name="my-skill", description="...", script_name="run.py")`
- **THEN** 脚本文件名为 `run.py` 而非默认的 `main.py`

#### Scenario: 创建后立即可搜索
- **WHEN** `create_skill` 成功返回
- **THEN** 调用 `search_skills("my-skill")` MUST 能检索到新创建的技能

#### Scenario: 拒绝非法技能名称
- **WHEN** Agent 调用 `create_skill(name="My Skill!")` （含大写或特殊字符）
- **THEN** 系统返回错误，错误信息说明命名规范（小写字母 + 连字符）

#### Scenario: 拒绝覆盖已存在技能（默认行为）
- **WHEN** `skill/my-skill/` 目录已存在，Agent 调用 `create_skill(name="my-skill", ...)`
- **THEN** 系统返回错误，提示技能已存在，需传 `overwrite=true` 才能覆盖

#### Scenario: 显式覆盖已存在技能
- **WHEN** Agent 调用 `create_skill(name="my-skill", ..., overwrite=True)`
- **THEN** 系统删除旧目录，重新创建，并重新注册到 registry

#### Scenario: 路径穿越防护
- **WHEN** Agent 调用 `create_skill(name="../../../etc/passwd", ...)`
- **THEN** 系统拒绝请求，返回非法名称错误

### Requirement: REST API 支持创建技能
系统 SHALL 提供 `POST /skills` HTTP 端点，接受 JSON body 创建技能，返回创建的 `SkillInfo`。

#### Scenario: HTTP 创建成功
- **WHEN** 客户端发送 `POST /skills` 携带合法 JSON body
- **THEN** 返回 HTTP 201，body 为创建的 `SkillInfo` JSON

#### Scenario: HTTP 创建失败（名称冲突）
- **WHEN** 客户端发送 `POST /skills`，技能已存在且未传 `overwrite`
- **THEN** 返回 HTTP 409 Conflict，body 包含错误描述

#### Scenario: HTTP 创建失败（参数校验）
- **WHEN** 客户端发送 `POST /skills`，`name` 字段不符合命名规范
- **THEN** 返回 HTTP 422 Unprocessable Entity
