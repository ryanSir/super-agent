## Why

当前 `src_deepagent` 支持技能的发现、搜索和执行，但缺乏**创建新技能**的能力。Agent 在完成任务后无法将可复用的能力固化为技能包，导致知识无法沉淀、重复劳动。参考 `src/skills/creator.py` 和 `init_skill.py` 已有创建逻辑，需将其集成到 `src_deepagent` 的工具体系中。

## What Changes

- 在 `src_deepagent/capabilities/` 下新增技能创建工具 `create_skill`，供 Agent 调用
- 实现技能脚手架生成：自动创建 `skill/<name>/SKILL.md`、`scripts/` 目录及示例脚本
- 在 Agent 工具集（`base_tools.py`）中注册 `create_skill` 工具
- 在 `factory.py` 中为适合的 Agent 角色（Researcher、Writer）开放创建权限
- 新增 REST API 端点 `POST /skills` 支持通过 HTTP 创建技能

## Non-goals

- 不支持技能的删除或版本管理
- 不支持技能的发布/上传到远程仓库
- 不修改现有技能的执行逻辑
- 不提供技能编辑（修改已有技能内容）功能

## Capabilities

### New Capabilities

- `skill-creation`: Agent 通过工具调用创建新技能包，包含脚手架生成、SKILL.md 写入、脚本文件初始化

### Modified Capabilities

- `skills`: 在现有 skills 规格中补充创建场景的接口定义（`SkillCreator` 接口及 `create_skill` 工具规格）

## Impact

- **新增文件**: `src_deepagent/capabilities/skill_creator.py`
- **修改文件**: `src_deepagent/capabilities/base_tools.py`（注册新工具）、`src_deepagent/agents/factory.py`（工具分配）、`src_deepagent/gateway/rest_api.py`（新增端点）
- **依赖**: 复用 `src/skills/creator.py` 逻辑或在 `src_deepagent` 内独立实现
- **风险**: 创建技能涉及文件系统写操作，属于 SAFE Worker 范畴（本地文件写入，无代码执行）
