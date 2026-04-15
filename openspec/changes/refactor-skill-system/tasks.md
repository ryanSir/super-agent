## 1. 数据模型变更

- [x] 1.1 `capabilities/skills/schema.py` — SkillMetadata 新增 `execution: Literal["native", "sandbox"] = "sandbox"` 字段
- [x] 1.2 `capabilities/skills/schema.py` — 确认 SkillInfo 模型无需变更（scripts/references/doc_content 保持不变）

## 2. Frontmatter 解析适配

- [x] 2.1 `capabilities/skills/registry.py` — `_parse_frontmatter()` 解析 `execution` 字段，无效值回退 `sandbox` 并记录警告日志
- [x] 2.2 `capabilities/skills/registry.py` — 精简 SkillRegistry，标记 `scan()` / `get_skill_summary()` / `search_skills()` / `list_skills()` 为 deprecated

## 3. Agent Factory 启用 SkillsToolset

- [x] 3.1 `orchestrator/agent_factory.py` — `create_orchestrator_agent()` 中 `include_skills=False` 改为 `include_skills=True`
- [x] 3.2 `orchestrator/agent_factory.py` — 添加 `skill_directories=[{"path": settings.skill_dir, "recursive": True}]` 参数
- [ ] 3.3 验证 `list_skills` / `load_skill` / `read_skill_resource` / `run_skill_script` 四个框架工具正确注入 Agent
- [ ] 3.4 验证 `SkillsToolset.get_instructions()` 自动注入 skill 摘要到 prompt，确认格式与现有 prompt 风格兼容

## 4. Sub-Agent 全量工具注入

- [x] 4.1 `agents/factory.py` — `create_sub_agent_configs()` 新增 `mcp_toolsets: list[Any] | None = None` 参数
- [x] 4.2 `agents/factory.py` — 三个预置角色配置统一注入全量 base tools（去掉 `plan_and_decompose`），移除 `_pick_tools` 按角色分配逻辑
- [x] 4.3 `agents/factory.py` — 每个角色配置新增 `include_skills=True` + `skill_directories` + `toolsets=mcp_toolsets`
- [x] 4.4 `gateway/rest_api.py` 或 `orchestrator/agent_factory.py` — 调用 `create_sub_agent_configs()` 时传入 `mcp_toolsets=plan.resources.mcp_toolsets`
- [ ] 4.5 验证 sub-agent 可调用 MCP 工具和框架 skill 工具

## 5. Context Builder 移除手动 skill 拼接

- [x] 5.1 `context/builder.py` — 移除 `build_dynamic_instructions()` 中 `<skill_system>` 段（第 106-113 行）
- [x] 5.2 `context/builder.py` — `skill_summary` 参数保留但标记 deprecated，函数体内忽略该参数
- [x] 5.3 `orchestrator/reasoning_engine.py` — `_resolve_resources()` 中移除 `skill_registry.get_skill_summary()` 调用

## 6. create_base_tools() 返回分组 dict

- [x] 6.1 `capabilities/base_tools.py` — `create_base_tools()` 返回值从 `list[Callable]` 改为 `dict[str, list[Callable]]`，按职责分组（native/sandbox/ui/memory/plan/skill_mgmt）
- [x] 6.2 `orchestrator/reasoning_engine.py` — `_resolve_resources()` 适配新的分组 dict 返回值
- [x] 6.3 `agents/factory.py` — `create_sub_agent_configs()` 从分组 dict 中排除 `plan` 组，其余全量注入
- [x] 6.4 `orchestrator/agent_factory.py` — 适配分组 dict，合并所有组传入 `create_deep_agent(tools=...)`

## 7. execute_skill 添加模式检查

- [x] 7.1 `capabilities/base_tools.py` — `execute_skill()` 开头添加 execution 模式检查：native skill 返回错误引导
- [x] 7.2 `capabilities/base_tools.py` — 移除 `search_skills()` base tool 函数（由框架 `list_skills` 替代）
- [x] 7.3 `capabilities/base_tools.py` — `create_base_tools()` 中移除 `search_skills` 的注册

## 8. System Prompt 路由引导

- [x] 8.1 `context/templates/` — 新建 `skill_routing.md` 模板，包含 native/sandbox 两种执行路径的引导说明（含 `run_skill_script` 用于简单脚本、`execute_skill` 用于复杂脚本的分层指引）
- [x] 8.2 `context/builder.py` — 在 `build_dynamic_instructions()` 中加载 `skill_routing` 模板（替代原 `<skill_system>` 段位置）

## 9. run_skill_script 能力验证

- [x] 9.1 确认 pydantic-deep 当前版本 `run_skill_script` 的能力边界：超时控制、stderr 处理、返回格式、参数传递
- [x] 9.2 如果 `run_skill_script` 满足简单脚本场景，在 `skill_routing.md` 中明确分层边界；否则所有脚本统一走 `execute_skill`

## 10. 现有 Skill 包适配

- [x] 10.1 检查 `skill/` 目录下所有 SKILL.md，确认无 `execution` 字段时默认行为为 sandbox（向后兼容验证）
- [x] 10.2 选择一个适合 native 模式的 Skill（如纯搜索/分析类），在 frontmatter 中添加 `execution: native` 作为示例

## 11. 集成测试

- [ ] 11.1 验证 native skill 完整流程：`list_skills` → `load_skill` → Base Tool 执行 → 返回结果
- [ ] 11.2 验证 sandbox skill 完整流程：`list_skills` → `execute_skill` → Pi Agent 沙箱执行 → 返回结果
- [ ] 11.3 验证混合场景：同一会话中先执行 native skill 再执行 sandbox skill
- [ ] 11.4 验证 sub-agent 执行 native skill：sub-agent 调用 `load_skill` → Base Tool + MCP Tool 执行
- [ ] 11.5 验证 sub-agent 执行 sandbox skill：sub-agent 调用 `execute_skill` → Pi Agent 沙箱执行
- [ ] 11.6 验证 `run_skill_script` 简单脚本执行（如有）
- [ ] 11.7 验证 `create_skill` 动态创建后 `list_skills` 可发现新 Skill
