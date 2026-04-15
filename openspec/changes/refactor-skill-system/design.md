## Context

当前 Skill 系统（`capabilities/skills/registry.py`）是完全自研的，包含目录扫描、frontmatter 解析、缓存、搜索等功能。同时 `base_tools.py` 中的 `execute_skill` 将所有 Skill 统一打包进沙箱由 Pi Agent 全权执行，导致 Skill 与 Base Tool / MCP Tool 完全隔离。

pydantic-deep 框架已内置 `SkillsToolset`，提供 `list_skills` / `load_skill` / `read_skill_resource` / `run_skill_script` 四个工具，支持三阶段渐进式加载、缓存和路径安全。当前项目在 `agent_factory.py:87` 已显式设置 `include_skills=False`，未启用此能力。

此外，框架的 Toolset 体系提供了 `get_instructions(ctx)` 自动注入 prompt、`FunctionToolset` 按领域组织工具、`CombinedToolset` 自动合并等能力，当前项目的 `create_base_tools()` 返回平铺函数列表，未利用这些机制。

参考 DeerFlow 的实践：Skill 作为"专家知识模板"由主 Agent 直接用 Base Tool 执行，脚本通过 bash tool 调用。我们的差异化在于用 Pi Agent 替代简单 bash，提供更智能的脚本执行能力。

## Goals / Non-Goals

**Goals:**
- 用 pydantic-deep `SkillsToolset` 替代自研 `SkillRegistry` 的扫描、加载、缓存逻辑
- 支持 native 模式：主 Agent 读取 SKILL.md 后直接用 Base Tool / MCP Tool 执行
- 保留 sandbox 模式：需要代码执行的 Skill 仍委托 Pi Agent
- SKILL.md frontmatter 新增 `execution` 字段实现模式分流
- 向后兼容：未标注 `execution` 的 Skill 默认走 sandbox

**Non-Goals:**
- 不实现 Skill Evolution（自动创建/改进 Skill）
- 不改变 Pi Agent 沙箱引擎本身
- 不修改现有 Skill 包目录结构
- 不引入独立的 Skill Router 层

## Decisions

### Decision 1: 用 SkillsToolset 替代 SkillRegistry

**选择**: 启用 `include_skills=True`，用框架的 `SkillsToolset` 替代自研 `SkillRegistry`

**替代方案**:
- A) 保留 SkillRegistry，仅修改 execute_skill → 维护两套加载逻辑，长期成本高
- B) 完全自研新的 Skill 加载器 → 重复造轮子，无法跟随框架升级

**理由**: 框架的 `list_skills` / `load_skill` / `read_skill_resource` / `run_skill_script` 与我们的三阶段加载（摘要→全文→资源/执行）完全对齐。框架还提供了缓存、路径穿越防护等我们缺失的能力。pydantic-ai 核心即将原生支持 skills（pydantic-ai#3780），提前对齐可降低未来迁移成本。

**影响**:
- `agent_factory.py`: `include_skills=False` → `include_skills=True`，配置 `skill_directories`
- `capabilities/skills/registry.py`: 大幅精简，仅保留 `register()` 用于动态注册
- `context/builder.py`: 移除手动 `<skill_system>` 拼接，由框架 `SkillsToolset.get_instructions()` 自动注入 skill 摘要；保留 `skill_routing.md` 模板引导 native/sandbox 分流
- `orchestrator/reasoning_engine.py`: `_resolve_resources()` 不再调用 `skill_registry.get_skill_summary()`

### Decision 2: SKILL.md frontmatter 新增 execution 字段

**选择**: 在 frontmatter 中新增 `execution: native | sandbox`（默认 `sandbox`）

**替代方案**:
- A) 由 Agent 自主判断走哪条路径 → 不可控，可能误判
- B) 根据是否有 scripts/ 目录自动判断 → 有脚本不代表必须走沙箱（脚本可能只是辅助模板）
- C) 在 ReasoningEngine 中做分流 → 职责不清，Skill 的执行模式应由 Skill 自身声明

**理由**: Skill 作者最清楚自己的 Skill 需要什么执行环境。声明式配置比推断更可靠，且对框架无侵入。

### Decision 3: Native 模式的执行方式

**选择**: 主 Agent 调用 `load_skill(name)` 读取完整 SKILL.md → 按指引使用 Base Tool / MCP Tool 执行

**替代方案**:
- A) 注入完整 SKILL.md 到 system prompt → 每轮都带着，token 浪费
- B) 新增专门的 `execute_native_skill` 工具 → 过度封装，Agent 已有足够工具

**理由**: 与 DeerFlow 验证过的模式一致。Agent 读完 SKILL.md 后自主决定用哪些工具，保持最大灵活性。SKILL.md 本身就是"操作手册"，不需要额外的执行器。

### Decision 4: Sandbox 模式分层 — run_skill_script + Pi Agent

**选择**: Sandbox skill 的脚本执行分两层：简单脚本用框架内置的 `run_skill_script`，复杂脚本（需要智能调试、多步执行、依赖安装）保留 `execute_skill` 委托 Pi Agent。

**替代方案**:
- A) 完全移除 execute_skill，所有脚本都通过框架 `run_skill_script` 执行 → 丢失 Pi Agent 的智能调试能力
- B) 保持现状（Pi Agent 全权负责）→ 简单脚本也要启动沙箱 + Pi Agent，开销过大
- C) 只保留 execute_skill，不用 run_skill_script → 浪费框架已有能力

**理由**: 框架的 `run_skill_script` 是轻量级脚本执行（subprocess 级别），适合"跑个 Python 脚本拿结果"的场景。Pi Agent 的价值在于复杂场景（理解意图、处理错误、安装依赖、多步调试）。两者互补，由 Agent 根据 SKILL.md 指引自行判断用哪个。

**需确认**: `run_skill_script` 的具体能力边界（超时控制、stderr 处理、返回格式），以决定分层的精确边界。

### Decision 5: 保留精简版 SkillRegistry 用于动态注册

**选择**: 不完全删除 `SkillRegistry`，保留 `register()` 和 `get()` 方法，作为 `create_skill` 工具的后端

**理由**: `create_skill` 动态创建 Skill 后需要立即注册到内存。框架的 `SkillsToolset` 基于文件系统发现，不支持运行时动态注入。保留一个精简的 registry 作为桥接层，在 `create_skill` 后同时写文件（让框架发现）和注册内存（立即生效）。

### Decision 6: Sub-Agent 全量注入 Base Tools + MCP Tools + SkillsToolset

**选择**: 所有 sub-agent 统一注入全量 base tools（去掉 `plan_and_decompose`）+ 共享主 Agent 的 MCP toolsets + 启用 `include_skills=True`

**替代方案**:
- A) 保持按角色精选工具 → native skill 在 sub-agent 中可能因缺少工具而无法执行
- B) Native skill 只在主 Agent 执行，sub-agent 只用 sandbox skill → 限制了 sub-agent 能力
- C) SKILL.md 声明 `required_tools`，系统按需过滤 → 增加复杂度，且 Skill 作者需要了解工具体系

**理由**:
- Base tools 总共 9 个（去掉 `plan_and_decompose`），加上 3 个框架 skill tools = 12 个，对 LLM 决策无压力
- Sub-agent 的角色差异化通过 `instructions`（角色指令）控制，而非限制工具集。"你擅长做什么"比"你只能用什么"更自然
- MCP toolsets 是无状态 HTTP 客户端（`FastMCPToolset`），可安全被多个 agent 共享
- 去掉按角色精选工具的维护成本（`agents/factory.py` 中的 `_pick_tools` 逻辑）

**影响**:
- `agents/factory.py`: `create_sub_agent_configs()` 新增 `mcp_toolsets` 参数；移除 `_pick_tools` 按角色分配逻辑，改为全量注入
- `agents/factory.py`: 每个角色配置新增 `include_skills=True` + `skill_directories` + `toolsets`
- `orchestrator/agent_factory.py` 或 `gateway/rest_api.py`: 调用 `create_sub_agent_configs()` 时传入 `mcp_toolsets`
- `plan_and_decompose` 仅保留在主 Agent，sub-agent 不应自己规划 DAG

### Decision 7: create_base_tools() 返回分组 dict，为 Toolset 化铺路

**选择**: 将 `create_base_tools()` 的返回值从 `list[Callable]` 改为按职责分组的 `dict[str, list[Callable]]`

**替代方案**:
- A) 保持平铺列表 → 后续迁移到 FunctionToolset 时需要重新梳理分组
- B) 直接改为 FunctionToolset → 改动范围过大，超出当前 change 边界

**理由**: 最小改动为后续 Toolset 化重构铺路。分组后 sub-agent 可精确排除 `plan` 组，未来每个组直接变成一个 FunctionToolset，过渡平滑。

```python
def create_base_tools(workers) -> dict[str, list[Callable]]:
    return {
        "native": [execute_rag_search, execute_db_query, execute_api_call, baidu_search],
        "sandbox": [execute_sandbox, execute_skill],
        "ui": [emit_chart],
        "memory": [recall_memory],
        "plan": [plan_and_decompose],
        "skill_mgmt": [create_skill],
    }
```

### Decision 8: Skill prompt 注入策略 — 框架自动 + 自定义路由引导

**选择**: Skill 摘要由框架 `SkillsToolset.get_instructions()` 自动注入（零代码），native/sandbox 分流引导由自定义 `skill_routing.md` 模板补充。

**替代方案**:
- A) 全部手动拼接 → 回到当前的维护负担
- B) 全部交给框架 → 框架不管 native/sandbox 分流引导

**理由**: 框架负责"有哪些 skill"，我们负责"怎么用 skill"。职责清晰，互不干扰。

## Risks / Trade-offs

**[框架 API 变更]** → pydantic-deep 的 SkillsToolset API 尚未稳定（文档提到将迁移到 pydantic-ai 核心）。**缓解**: 通过薄适配层隔离框架 API，变更时只改适配层。

**[Native Skill 的 Token 开销]** → Agent 调用 `load_skill` 后完整 SKILL.md 进入上下文，复杂 Skill 文档可能很长。**缓解**: SKILL.md 编写规范要求控制在 2000 token 以内；`read_skill_resource` 按需加载详细资源。

**[向后兼容]** → 现有 Skill 没有 `execution` 字段。**缓解**: 默认值为 `sandbox`，行为与当前完全一致，零迁移成本。

**[Native Skill 执行质量]** → 主 Agent 按 SKILL.md 指引执行，质量依赖 SKILL.md 的编写质量和 Agent 的理解能力。**缓解**: 提供 SKILL.md 编写模板和最佳实践文档；复杂流程建议用 sandbox 模式。

**[Sub-Agent 全量工具的 Token 开销]** → 每个 sub-agent 从精选 4-6 个工具变为 12 个，system prompt 中工具描述增加约 1000-1500 token。**缓解**: sub-agent 使用 subagent 模型（更快更便宜），且 `context_manager_max_tokens` 已设置为 100K，工具描述增量可忽略。

**[MCP Toolset 共享的并发安全]** → 多个 sub-agent 并行执行时共享同一批 `FastMCPToolset` 实例。**缓解**: `FastMCPToolset` 底层是无状态 HTTP 客户端，每次 `call_tool` 独立发起请求，无共享状态，并发安全。

## Migration Plan

1. **Phase 1 — 启用 SkillsToolset**: 修改 `agent_factory.py`，设置 `include_skills=True` + `skill_directories`。此时框架的 `list_skills` / `load_skill` / `read_skill_resource` 立即可用，与现有 `search_skills` / `execute_skill` 并存。
2. **Phase 2 — 扩展 frontmatter**: `SkillMetadata` 新增 `execution` 字段，更新 frontmatter 解析。
3. **Phase 3 — Sub-Agent 工具统一**: `agents/factory.py` 全量注入 base tools + MCP toolsets + SkillsToolset，移除 `_pick_tools` 按角色分配逻辑。
4. **Phase 4 — 实现 native 路径**: 修改 system prompt 引导 Agent 对 native skill 使用 `load_skill` → Base Tool 流程。
5. **Phase 5 — 收窄 execute_skill**: 添加 execution 模式检查，sandbox-only。
6. **Phase 6 — 清理**: 移除 `context/builder.py` 中手动 skill_summary 拼接，精简 SkillRegistry。

**回滚策略**: 每个 Phase 独立可回滚。最坏情况回退到 `include_skills=False` + 现有 SkillRegistry。

## Open Questions

- pydantic-deep 当前版本是否支持 `BackendSkillsDirectory`？需要确认版本兼容性。
- `SkillsToolset` 的 `list_skills` 返回格式是否满足现有 system prompt 的摘要需求？可能需要适配。
- `create_skill` 动态创建后，`SkillsToolset` 是否能自动发现新文件？还是需要手动触发重新扫描？
- `run_skill_script` 的具体能力边界：超时控制、stderr 处理、返回格式、是否支持参数传递？以此决定与 `execute_skill`（Pi Agent）的分层边界。
- `SkillsToolset.get_instructions()` 输出的 XML 格式是否与现有 prompt 风格兼容？是否需要自定义模板覆盖？

## Future Work（不在当前 change 范围）

- **Base Tools Toolset 化重构**: 将 `create_base_tools()` 的分组 dict 进一步迁移为独立的 `FunctionToolset`（NativeToolset / SandboxToolset / UIToolset），利用框架的 `CombinedToolset` 自动合并、`prepare()` hook 按执行模式动态裁剪工具、`get_instructions()` 分散 prompt 注入。
- **观测性 Toolset Wrapper**: 用自定义 Toolset Wrapper 统一处理 Langfuse Span 追踪 + SSE tool_result 事件推送，替代当前逐函数包装的 `_wrap_with_tool_result`。
- **defer_loading() 渐进式工具加载**: 利用框架的 `defer_loading()` 实现工具不全量注入 prompt 的设计目标。
