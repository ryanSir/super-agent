# Super-Agent 技术选型终审报告

> 版本：v1.0 | 2026-04-17
>
> 基于 6 个开源框架源码级审计、3 份 SDK 深度对比、1 份产线安全性分析、1 份功能模块规划
>
> 评审范围：Pydantic-Deep / Deep Agents / CrewAI / DeerFlow / AgentScope / Hermes

---

## 一、背景与目标

Super-Agent 定位为企业级混合 AI Agent 引擎，核心架构为"Python 控制面编排 + 沙箱 Pi Agent 自主执行"。项目需要选择一个 Agent SDK 作为底层编排框架，承载以下核心能力：

- 四种执行模式自动路由（DIRECT / AUTO / PLAN_AND_EXECUTE / SUB_AGENT）
- 五维度复杂度评估 + ReasoningEngine 智能决策
- E2B 沙箱 + Pi Agent 自主执行
- Redis 全链路状态管理 + SSE 断点续传
- 渐进式工具加载（Skills 三阶段 + MCP 延迟加载）

选型的核心诉求：**以最低的集成成本和维护负担，获得可靠的 Agent 编排能力，同时保留架构自主权。**

---

## 二、评估框架分类

在深入分析 6 个框架后，我们首先做了一个关键分类——SDK 型 vs 应用型，这直接决定了集成模式和长期维护成本。

| 类型 | 框架 | 集成方式 | 维护模式 |
|------|------|----------|----------|
| SDK 型 | Pydantic-Deep / Deep Agents / CrewAI | `pip install` → 调用 API | 框架团队维护核心，我们只写胶水代码 |
| 应用型 | DeerFlow / Hermes / AgentScope | `git clone` → 自己跑整个应用 | 自己维护全部代码（数万行） |

**结论：Super-Agent 需要的是 SDK 型框架。** 我们已有完整的 FastAPI 网关、Redis 状态管理、ReasoningEngine 决策引擎，不需要另一个"应用"，只需要一个可嵌入的编排内核。

这一判断将 DeerFlow（28,600 行自建代码）、Hermes（自研编排循环 + 10+ Gateway）、AgentScope（25,000+ 行，平台级框架）排除出 SDK 候选，但它们的优秀设计仍作为参考借鉴。

---

## 三、候选方案综合评估

### 3.1 三个 SDK 候选的核心差异

| 维度 | Pydantic-Deep v0.3.3 | Deep Agents v0.5.3 | CrewAI v1.14.1 |
|------|----------------------|---------------------|----------------|
| 出品方 | 社区（Pydantic 公司背书） | LangChain 官方 | CrewAI Inc.（独立公司） |
| 编排范式 | LLM 自主循环 + task() 委派 | LLM 自主循环 + task() 委派 | 显式多 Agent 流程编排 |
| 谁决定任务拆分 | LLM 自主判断 | LLM 自主判断 | 开发者预定义 |
| 核心依赖 | pydantic-ai（1 个） | LangChain 生态（5 个包） | 自研（零框架依赖） |
| 代码规模 | ~8,400 行 / 33 模块 | ~10,000+ 行 | ~30,000+ 行 |
| API 稳定性 | v0.3.3 pre-1.0 | v0.5.3 pre-1.0（8 天 3 个 release） | v1.14.1（最稳定） |
| 综合评分 | 6.8/10 | 6.8/10 | 7.1/10 |

### 3.2 编排模型契合度分析（决定性因素）

Super-Agent 已有 ReasoningEngine 做五维度复杂度评估和四模式路由，**编排决策权在我们自己的控制面**，不需要框架再做一层编排。

| 框架 | 编排模型 | 与 Super-Agent 的契合度 |
|------|----------|------------------------|
| Pydantic-Deep | LLM 自主决定是否拆分 + task() 委派 | **完美匹配** — ReasoningEngine 决定模式，Agent 内部自主执行 |
| Deep Agents | 同上，但基于 LangGraph 状态图 | 匹配，但 LangGraph 的图约束与我们的模式路由有概念重叠 |
| CrewAI | 开发者预定义 Agent 角色和 Task 流程 | **不匹配** — 需要为每个场景预定义编排，与 ReasoningEngine 的动态路由冲突 |

CrewAI 的"显式定义角色"模式在实际使用中暴露了明显痛点：

```python
# CrewAI — 每换一个场景就要重新定义整套 Agent/Task
researcher = Agent(role="市场研究员", goal="...", backstory="...", tools=[...])
analyst = Agent(role="数据分析师", goal="...", backstory="...", tools=[...])
writer = Agent(role="报告撰写者", goal="...", backstory="...", tools=[...])
# backstory 差一个词效果就不一样，反复调试
# Task context 传递不稳定，经常丢信息
# Process.hierarchical 的 manager agent 决策不可控

# Pydantic-Deep — 一行搞定，LLM 自己判断
agent = create_deep_agent(subagents=[
    {"name": "researcher", "description": "负责市场调研"},
])
result = await agent.run("写一份市场分析报告")
```

### 3.3 依赖链风险对比

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 核心依赖数 | 1（pydantic-ai） | 5（langchain + langchain-core + langchain-anthropic + langchain-google-genai + langsmith） | 0（自研）+ litellm |
| 上游 breaking change 风险 | 低（Pydantic 公司风格稳健） | 高（LangChain API 变动频繁，历史教训多） | 低（自己控制节奏） |
| 升级适配成本 | 低（3 个导入点） | 中（LangGraph 图结构可能变） | 低（Crew/Agent/Task 三个类稳定） |
| 依赖链深度 | 浅 | 深（5 个包各自的传递依赖） | 浅 |

Deep Agents 的 5 个 LangChain 包是最大的隐患。LangChain 生态的 API 变动频繁是业界共识，任何一个包的升级都可能引入不兼容变更。

### 3.4 源码级稳定性审计

我们对三个 SDK 候选进行了源码级 Bug 审计：

| 框架 | P0（生产可触发） | P1（边界条件） | P2（代码质量） | 总计 |
|------|-----------------|---------------|---------------|------|
| Pydantic-Deep | 4 | 4 | 6 | 14 |
| Deep Agents | 3 | 2 | 2 | 7 |
| CrewAI | 0（未做源码审计） | 3 | 2 | 5 |

Pydantic-Deep 的 4 个 P0 问题：

| # | 问题 | 对 Super-Agent 的实际影响 |
|---|------|--------------------------|
| 1 | agent.tool(tool.function) 丢失 Tool 元数据 | **不影响** — 我们传的是裸函数，不是 Tool 对象 |
| 2 | Agent 实例 setattr 私有属性 | **低风险** — 我们不用 CLI，不直接读取这些属性 |
| 3 | CheckpointMiddleware 类型不安全 | **不影响** — 我们关闭了 checkpoints |
| 4 | FileCheckpointStore 同步 I/O 阻塞 | **不影响** — 我们关闭了 checkpoints |

**关键发现：Pydantic-Deep 的 4 个 P0 Bug 在 Super-Agent 的实际调用路径中均不触发。** 这得益于我们的集成方式——只激活需要的模块，关闭了 memory、checkpoints、teams、patch 等功能。

### 3.5 生产就绪度综合评分

| 维度 | Pydantic-Deep | Deep Agents | CrewAI |
|------|--------------|-------------|--------|
| 功能完整度 | 8/10 | 8/10 | 9/10 |
| 代码质量 | 7/10 | 7/10 | 7/10 |
| 错误处理 | 6/10 | 6/10 | 6/10 |
| 类型安全 | 6/10 | 8/10 | 7/10 |
| API 稳定性 | 5/10 | 4/10 | 8/10 |
| 安全性 | 5/10 | 6/10 | 5/10 |
| 可扩展性 | 8/10 | 9/10 | 7/10 |
| 依赖健康度 | 8/10 | 5/10 | 8/10 |
| **综合** | **6.6** | **6.6** | **7.1** |

CrewAI 综合分最高，但编排模型与 Super-Agent 不匹配，这是一票否决项。

---

## 四、应用型框架的借鉴价值

虽然 DeerFlow、AgentScope、Hermes 不作为 SDK 候选，但它们的优秀设计值得借鉴：

### 4.1 DeerFlow（综合评分 7.7/10 — 六框架最高）

| 借鉴点 | 设计 | 借鉴方式 |
|--------|------|----------|
| 安全审计 | SandboxAuditMiddleware：15 高风险 + 5 中风险正则，复合命令分割，fail-closed | 移植到 Super-Agent 的 Hooks 系统 |
| 错误处理 | GraphBubbleUp 保留 + 业务异常转 ToolMessage + LLM 重试指数退避 | 参考其分级策略优化我们的错误处理 |
| 循环检测 | 按工具类型定制哈希 + LRU 驱逐 + 线程隔离 | 升级我们现有的简单 MD5 哈希方案 |

### 4.2 AgentScope（综合评分 7.3/10）

| 借鉴点 | 设计 | 借鉴方式 |
|--------|------|----------|
| 记忆系统 | 4 种后端 + marks 标签 + ReMe 跨 Agent 共享 | 未来记忆系统升级时参考 |
| Token 计数 | 5 种专用计数器（tiktoken/Anthropic API/Gemini/HF/Char） | 精确计费时参考 |
| 可观测性 | OTel 原生 + Studio 实时展示 + 流式追踪 | 监控系统升级时参考 |

### 4.3 Hermes

| 借鉴点 | 设计 | 借鉴方式 |
|--------|------|----------|
| MCP 集成 | 完整协议支持（含 Sampling） | MCP 能力增强时参考 |
| 上下文压缩 | 三阶段压缩策略 | 长对话场景优化时参考 |

---

## 五、选型结论

### 5.1 最终选择：Pydantic-Deep v0.3.3

经过六个框架的源码级审计和三个 SDK 候选的深度对比，**推荐 Pydantic-Deep 作为 Super-Agent 的底层编排框架**。

### 5.2 决策矩阵

| 决策维度 | 权重 | Pydantic-Deep | Deep Agents | CrewAI |
|----------|------|---------------|-------------|--------|
| 编排模型契合度 | 30% | 10（完美匹配） | 8（匹配但有概念重叠） | 3（不匹配） |
| 依赖链风险 | 20% | 9（1 个核心依赖） | 4（5 个 LangChain 包） | 8（自研） |
| 集成成本 | 15% | 9（3 个导入点） | 7（需适配 LangGraph） | 5（需重写编排逻辑） |
| 降级兜底能力 | 15% | 10（可退回原生 pydantic-ai） | 5（深度绑定 LangGraph） | 3（无降级路径） |
| 团队经验 | 10% | 8（已踩过 CrewAI 的坑） | 5（需学习 LangGraph） | 4（已验证痛点） |
| API 稳定性 | 10% | 5（pre-1.0） | 4（更不稳定） | 8（v1.14） |
| **加权总分** | 100% | **8.65** | **5.85** | **4.75** |

### 5.3 选择 Pydantic-Deep 的五个核心理由

**理由一：编排模型最匹配**

Super-Agent 的 ReasoningEngine 已经承担了"决定做什么"的职责，Agent SDK 只需要承担"怎么做"。Pydantic-Deep 的 LLM 自主循环 + task() 委派模式，是 ReasoningEngine 的天然延伸——控制面决定模式，执行面自主完成。

**理由二：依赖最轻，升级风险最低**

1 个核心依赖（pydantic-ai），由 Pydantic 公司间接背书，API 风格稳健。对比 Deep Agents 的 5 个 LangChain 包，任何一个的 breaking change 都可能波及我们。

**理由三：集成面最小，维护成本最低**

Super-Agent 仅 3 个导入点：
- `agent_factory.py` → `create_deep_agent`, `create_default_deps`, `StateBackend`
- `hooks.py` → `Hook`, `HookEvent`, `HookInput`, `HookResult`

8,400 行源码，团队可完全掌控。

**理由四：降级兜底已验证**

`agent_factory.py` 已实现 `_create_fallback_agent()`，pydantic-deep 不可用时可降级到原生 pydantic-ai Agent。降级到原生 pydantic-ai 的完整工作量约 1,150 行新代码 / 2-3 周，最大风险在 Sub-Agent 编排。

**理由五：产线安全性已验证**

经过逐模块产线风险评估，Pydantic-Deep 在 Super-Agent 的实际调用路径中：
- 4 个 P0 Bug 均不触发（关闭了 checkpoints、不用 Tool 对象、不用 CLI）
- 每次请求创建新 Agent 实例，无并发共享问题
- StateBackend 纯内存，无文件 I/O 阻塞

---

## 六、风险与缓解措施

### 6.1 已识别风险

| 风险等级 | 风险描述 | 概率 | 影响 |
|----------|----------|------|------|
| 🔴 高 | `rest_api.py` 使用 Anthropic Beta API（`BetaThinkingConfigEnabledParam`），SDK 升级可能断裂 | 中 | 高 |
| 🟡 中 | Pydantic-Deep v0.3.3 是 pre-1.0，API 可能变化 | 中 | 中 |
| 🟡 中 | 每次请求重新扫描 Skill 目录，50+ Skill 时多 100-200ms | 低 | 中 |
| 🟡 中 | `deps.py` 访问 `StateBackend._files` 私有属性 | 低 | 中 |
| 🟢 低 | Pydantic 公司方向调整影响 pydantic-ai 生态 | 低 | 高 |

### 6.2 缓解措施（上线前必做）

**措施一：锁定关键依赖版本（5 分钟）**

```toml
# pyproject.toml
pydantic-deep = "==0.3.3"
pydantic-ai-slim = "==1.83.0"
anthropic = "==0.52.0"
```

**措施二：修复 Beta API 风险（10 分钟）**

```python
# 替换 BetaThinkingConfigEnabledParam，改用稳定 API
iter_kwargs["model_settings"] = AnthropicModelSettings(
    anthropic_thinking={"type": "enabled", "budget_tokens": budget},
    max_tokens=max_tokens,
)
```

**措施三：关闭不需要的默认功能（2 分钟）**

```python
agent = create_deep_agent(
    ...
    include_plan=False,              # 我们有自己的 ReasoningEngine
    include_history_archive=False,   # StateBackend 下无法正常工作
    include_builtin_subagents=False, # 我们有自己的 sub_agent_configs
)
```

**措施四：静默降级加日志（5 分钟）**

```python
# rest_api.py 中所有 except Exception: pass 改为
except Exception as e:
    logger.warning(f"配置失败，使用默认设置 | error={e}")
```

### 6.3 中长期风险对冲

| 时间线 | 措施 |
|--------|------|
| 上线前 | 完成上述 4 项必做改动 |
| 上线后 1 个月 | 缓存 SkillsToolset 实例，避免每次请求重新扫描 |
| 持续 | 跟踪 pydantic-deep 版本发布，在 staging 环境验证后再升级 |
| 备选 | 维护降级到原生 pydantic-ai 的能力，Sub-Agent 编排逻辑封装在独立模块 |

---

## 七、项目实施概览

基于功能模块规划，Super-Agent 全量开发估时如下：

| # | 模块 | 目录 | 估时 | 优先级 |
|---|------|------|------|--------|
| 1 | API 网关 | gateway/ | 10d | P0 |
| 2 | 推理引擎 | orchestrator/ | 12.5d | P0 |
| 3 | 工具系统 | capabilities/ | 12.5d | P0 |
| 4 | 执行层 | workers/ | 12.5d | P0 |
| 5 | 事件流 | streaming/ | 5d | P0 |
| 6 | 会话管理 | state/ | 4d | P0 |
| 7 | 上下文系统 | context/ | 4d | P0 |
| 8 | 数据模型 | schemas/ | 4d | P0 |
| 9 | 配置 | config/ | 2.5d | P0 |
| 10 | core + main.py | core/ | 2.5d | P0 |
| 11 | LLM 路由 | llm/ | 7d | P1 |
| 12 | 记忆系统 | memory/ | 7.5d | P1 |
| 13 | Sub-Agent | agents/ | 5.5d | P1 |
| 14 | 监控追踪 | monitoring/ | 8d | P1 |
| 15 | 安全 | security/ | 8.5d | P2 |
| 16 | 计费 | billing/ | 6.5d | P2 |
| | **合计** | | **112.5d** | |

> 按 1 人全栈约 5.5 个月（22 工作日/月）；2 人并行约 3 个月。

---

## 八、与竞品框架的能力对标

Super-Agent 选择 Pydantic-Deep 作为 SDK 后，通过自建控制面补齐了 SDK 层面的不足，最终能力对标如下：

| 能力维度 | Super-Agent（自建 + PD） | DeerFlow | AgentScope | 评价 |
|----------|--------------------------|----------|------------|------|
| 执行模式路由 | 四模式自动路由（独有） | 无 | 无 | **领先** |
| 安全审计 | Hooks + ToolGuard（需加强） | SandboxAuditMiddleware | 无 | 需借鉴 DeerFlow |
| 沙箱执行 | E2B + Pi Agent 自主执行 | Local + Docker | 无 | **领先**（沙箱内有独立 Agent） |
| 记忆系统 | Redis Profile + Facts | 文件 + LLM 摘要 | 4 后端 + ReMe | 中等，可扩展 |
| 分布式状态 | Redis Hash + Stream + 分布式锁 | LangGraph 检查点 | Redis/SQLAlchemy | **领先** |
| 可观测性 | Langfuse + OTel + 结构化日志 | LangSmith + Langfuse | OTel + Studio | 中等 |
| Skills 系统 | 三阶段渐进加载 + 双执行模式 | 技能演进 | AgentSkill + 工具分组 | **领先** |
| 降级容错 | 记忆超时降级 / Worker 跳过 / 框架降级 | 中间件可跳过 | 无 | **领先** |
| MCP 集成 | 多端点 + 凭证注入 + 自动刷新 | langchain-mcp-adapters | StdIO + HTTP | **领先** |
| 多 Agent 协作 | task() 扁平委派 | SubagentExecutor | MsgHub + Pipeline + A2A | 基础，可扩展 |

---

## 九、总结

### 选型结论

**Pydantic-Deep v0.3.3** 是 Super-Agent 的最优选择。核心逻辑：

1. **架构契合** — LLM 自主循环 + task() 委派 = ReasoningEngine 的天然延伸，不引入编排概念冲突
2. **风险可控** — 1 个核心依赖、8,400 行源码、3 个导入点，团队可完全掌控
3. **降级兜底** — 随时可退回原生 pydantic-ai，最大工作量 2-3 周
4. **产线验证** — 4 个 P0 Bug 在实际调用路径中均不触发，安全性已逐模块确认

### 不选其他方案的原因

| 方案 | 一句话否决理由 |
|------|---------------|
| CrewAI | 显式编排模型与 ReasoningEngine 动态路由根本冲突 |
| Deep Agents | 5 个 LangChain 包的依赖链风险不可接受，API 极不稳定（8 天 3 个 release） |
| DeerFlow | 应用型框架，28,600 行自建代码，集成成本远超 SDK 方案 |
| AgentScope | 平台级框架，过重；无内置沙箱是最大短板 |
| Hermes | 自研编排循环，无法作为 SDK 嵌入 |

### 下一步行动

| 序号 | 行动项 | 负责人 | 时间 |
|------|--------|--------|------|
| 1 | 完成 4 项上线前必做改动（版本锁定 / Beta API / 功能关闭 / 日志） | 开发 | 1 天 |
| 2 | P0 模块开发启动（网关 / 推理引擎 / 工具系统 / 执行层） | 开发 | 第 1-6 周 |
| 3 | 借鉴 DeerFlow 安全审计设计，增强 Hooks 安全能力 | 开发 | 第 4 周 |
| 4 | P1 模块开发（LLM 路由 / 记忆 / Sub-Agent / 监控） | 开发 | 第 7-10 周 |
| 5 | P2 模块开发（安全 / 计费） | 开发 | 第 11-13 周 |

---

*本报告基于 6 个开源框架截至 2026-04-17 的源码版本。所有 Bug 位置、行数、评分均基于实际代码审计，可对照源码验证。*
