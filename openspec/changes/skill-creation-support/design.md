## Context

`src_deepagent` 已有完整的技能发现（`SkillRegistry`）、搜索（`search_skills`）和执行（`execute_skill`）链路，但缺少**创建**环节。`src/skills/creator.py` 已实现完整的脚手架生成逻辑，但它依赖 `src.core.logging` 和 `src.skills.*` 等 `src/` 命名空间，无法直接在 `src_deepagent` 中 import。

当前 `src_deepagent/capabilities/base_tools.py` 提供 `execute_skill` 和 `search_skills` 两个工具函数，通过 `CapabilityRegistry` 注入 Agent。新增 `create_skill` 工具需遵循相同模式。

## Goals / Non-Goals

**Goals:**
- 在 `src_deepagent` 内实现独立的 `SkillCreator`，不依赖 `src/` 命名空间
- 新增 `create_skill` 工具函数，注册到 `base_tools.py` 并分配给 Researcher/Writer Agent
- 新增 REST API `POST /skills` 端点，支持 HTTP 调用创建技能
- 创建后自动调用 `skill_registry.register()` 使新技能立即可用

**Non-Goals:**
- 不复用 `src/skills/creator.py`（避免跨命名空间依赖）
- 不支持技能删除、版本管理、远程发布
- 不提供技能内容编辑功能

## Decisions

### 决策 1：独立实现 vs 复用 src/skills/creator.py

**选择：独立实现** `src_deepagent/capabilities/skill_creator.py`

- `src/` 和 `src_deepagent/` 是两个独立的服务边界，交叉 import 会引入隐式耦合
- `src/skills/creator.py` 依赖 `src.core.logging` 和 `src.skills.init_skill`，迁移成本高
- `src_deepagent` 版本可以更精简，只保留 `create_skill` 核心路径，去掉模板模式

**替代方案**：将 `src/skills/creator.py` 提取为共享库 → 改动范围过大，超出本次变更范围。

### 决策 2：工具风险等级

**选择：SAFE Worker**（Native 执行，不走 E2B 沙箱）

- 创建技能只涉及本地文件系统写操作（`skill/` 目录），无代码执行
- 与 `execute_skill`（DANGEROUS，走 E2B）明确区分
- 文件写入路径限定在 `skill/<name>/`，不允许路径穿越

### 决策 3：API 端点设计

`POST /skills` 接受 JSON body，返回创建的 `SkillInfo`：

```json
{
  "name": "my-skill",
  "description": "技能描述",
  "script_name": "main.py",
  "script_content": "...",  // 可选
  "doc_content": "..."      // 可选
}
```

与现有 `/skills/{name}/execute` 端点保持 RESTful 风格一致。

### 决策 4：Agent 工具分配

- **Researcher Agent**：开放 `create_skill`（研究后固化能力）
- **Writer Agent**：开放 `create_skill`（生成内容类技能）
- **Analyst Agent**：不开放（分析场景不需要创建技能）

## Risks / Trade-offs

- **文件系统写入风险** → 对 `name` 字段做严格校验（`^[a-z][a-z0-9-]*$`），防止路径穿越
- **同名覆盖风险** → 默认拒绝覆盖已存在的技能目录，需显式传 `overwrite=true`
- **Registry 热更新** → 创建后立即调用 `skill_registry.register()`，但已运行的 Agent 实例不会感知，下次请求才生效
- **src/ 与 src_deepagent/ 技能目录共享** → 两者共用同一个 `skill/` 目录，创建的技能对两个服务均可见，这是预期行为
