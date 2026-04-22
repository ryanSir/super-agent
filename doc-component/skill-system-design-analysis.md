# Skill 系统设计分析

> Super-Agent Skill 架构 vs DeerFlow & pydantic-deep — 设计决策、理论依据与框架复用

## 架构定位

```
                    DeerFlow                Super-Agent (当前)           pydantic-deep 原生
                    ──────                  ─────────────────           ──────────────────
Skill 本质          知识模板                知识模板 + 执行包            知识模板
脚本执行            bash tool (subprocess)  Pi Agent (智能) +            run_skill_script
                                           run_skill_script (轻量)      (subprocess)
工具访问            全量 base tool          全量 base tool + MCP         框架内置 tool
Sub-Agent 支持      有（全量工具）          有（全量工具 + MCP + Skill）  无内置编排
执行模式分流        无（统一 native）       native / sandbox 声明式       无（统一 native）
```

## 一、与 DeerFlow 的关键差异

### 1. 脚本执行的智能程度不同

DeerFlow 的脚本执行是"盲执行" — Agent 通过 bash tool 跑 `node ./scripts/generate.js '<payload>'`，脚本失败了只能拿到 stderr，Agent 自己判断怎么重试。

当前设计保留了 Pi Agent 作为复杂脚本的执行层。Pi Agent 不是简单的 subprocess，它是一个有推理能力的 agent，能理解脚本意图、安装缺失依赖、处理中间错误、多步调试。这对应了 Michael Wooldridge 在 *An Introduction to MultiAgent Systems* 中提出的 **Cognitive Agent** 概念 — agent 不仅执行动作，还能对执行过程进行推理和自适应。

同时引入了框架的 `run_skill_script`（LocalSkillScriptExecutor，30s 超时 subprocess）处理简单脚本，避免所有脚本都走重量级的 Pi Agent。这是 **分层执行策略**（Tiered Execution），与微服务架构中"轻量请求走 edge function，重量请求走 full service"的思路一致。

```
执行分层：
┌─────────────────────────────────────────────────────┐
│  简单脚本（跑完拿结果）                               │
│  → run_skill_script (subprocess, 30s timeout)        │
├─────────────────────────────────────────────────────┤
│  复杂脚本（需要调试/安装依赖/多步执行）                │
│  → execute_skill → Pi Agent (沙箱, 智能推理)          │
└─────────────────────────────────────────────────────┘
```

### 2. 执行模式的声明式分流

DeerFlow 没有 native/sandbox 的区分 — 所有 skill 都是 native 模式，脚本通过 bash tool 执行。这在安全性上有隐患：任意脚本在宿主环境执行，没有沙箱隔离。

当前设计通过 SKILL.md frontmatter 的 `execution: native | sandbox` 字段实现声明式分流。这遵循了 **Convention over Configuration** 原则（Ruby on Rails 社区推广），同时保持了 **Principle of Least Privilege** — sandbox skill 在隔离环境执行，native skill 只有知识注入没有代码执行权限。

```yaml
# Skill 作者声明执行模式，系统自动路由
---
name: cost-reduction-triz
execution: native        # 纯知识引导，主 Agent 直接执行
---

---
name: ai-ppt-generator
execution: sandbox       # 需要代码执行，Pi Agent 沙箱执行
---
```

### 3. MCP 工具的深度集成

DeerFlow 的工具体系是封闭的 — 只有内置的 bash/file/web 等工具。当前设计通过 `FastMCPToolset` 将 MCP 协议工具注入主 Agent 和所有 Sub-Agent，native skill 可以在 SKILL.md 中引导 Agent 调用任意 MCP 工具。

这实现了 **Open-Closed Principle** — 系统对扩展开放（通过 MCP 协议接入新工具），对修改关闭（不需要改代码就能增加工具能力）。

## 二、与 pydantic-deep 原生能力的关系

### 复用的框架能力（6 项）

| 框架能力 | 替代的自研代码 | 收益 |
|---------|-------------|------|
| `SkillsToolset`（4 个工具） | 自研 `SkillRegistry` 的 scan/search/get_summary | 减少 ~300 行代码，获得路径穿越防护 + 缓存 |
| `get_instructions(ctx)` | `builder.py` 手动拼接 `<skill_system>` | Skill prompt 自动注入，零维护 |
| `SkillsDirectory` 文件发现 | `SkillRegistry.scan()` 目录扫描 | 支持递归、深度限制、frontmatter 校验 |
| `LocalSkillScriptExecutor` | 无（之前全走 Pi Agent） | 简单脚本轻量执行，30s 超时 |
| `BackendSkillsDirectory` | 无 | 沙箱内 skill 发现能力（预留） |
| `FunctionToolset` 分组机制 | 平铺函数列表 | 工具按职责组织，为 Toolset 化铺路 |

### 自研保留的能力（5 项）

| 自研能力 | 保留原因 |
|---------|---------|
| Pi Agent 沙箱执行 | 智能脚本调试是差异化能力，框架 subprocess 无法替代 |
| `execute_skill` base tool | Pi Agent 的入口，框架无对应 |
| `create_skill` 动态创建 | 框架基于文件发现，不支持运行时注入 |
| SSE 事件推送 + Langfuse 追踪 | 领域特有的观测性需求 |
| `skill_routing.md` 路由引导 | native/sandbox 分流是自研概念，框架不管 |

这体现了 **Strategic Design** 中的核心域/支撑域划分（Eric Evans, *Domain-Driven Design*）：

- **核心域**（自研）：Pi Agent 智能执行、执行模式分流 — 这是竞争优势
- **支撑域**（复用框架）：文件发现、缓存、路径安全 — 这是通用能力，不值得自研

## 三、Sub-Agent 工具统一的设计依据

当前设计将所有 Sub-Agent 统一注入全量 base tools + MCP toolsets + SkillsToolset，角色差异化通过 instructions 控制。

### 1. Capability vs Role 分离

传统 RBAC 按角色限制权限（researcher 只能搜索，analyst 只能查数据库）。但在 LLM Agent 场景下，工具限制带来的问题大于收益：

- native skill 可能需要任意工具组合，按角色限制会导致执行失败
- LLM 的工具选择能力足够强，不需要通过限制工具来"帮助"它聚焦
- 维护按角色的工具映射表成本高，每加一个工具要更新所有角色

改为"全量工具 + 角色指令"后，Sub-Agent 的行为由 instructions 中的专业知识引导，而非工具限制。这与 Herbert Simon 的 **Bounded Rationality** 理论一致 — 通过提供正确的决策框架（instructions）而非限制选项（tools）来引导行为。

### 2. 工具数量在 LLM 舒适区内

9 个 base tools + 4 个 skill tools = 13 个。根据 Anthropic 和 OpenAI 的实践，LLM 在 20 个工具以内的选择准确率没有显著下降。Google DeepMind 的 Toolformer 研究也表明，工具数量对 LLM 决策质量的影响远小于工具描述的清晰度。

```
工具注入对比：

之前（按角色精选）：
  researcher: 6 tools    analyst: 4 tools    writer: 4 tools
  → 维护 3 套映射，native skill 可能缺工具

现在（全量统一）：
  所有角色: 13 tools (9 base + 4 skill)
  → 零维护，native skill 完整执行
```

## 四、渐进式加载的信息论依据

当前设计的三阶段加载（摘要 → 全文 → 资源/脚本）对应了 **Information Foraging Theory**（Pirolli & Card, 1999）中的 **信息气味（Information Scent）** 概念：

```
Stage 1: list_skills()           → 低成本嗅探（~100 token）
Stage 2: load_skill(name)        → 中成本深入（~500-2000 token）
Stage 3: read_skill_resource()   → 高成本获取（按需）
         run_skill_script()
```

Agent 先通过低成本的摘要判断"气味"是否匹配，再决定是否投入更多 token 深入。这与人类在信息检索中的行为模式一致，也是 RAG 系统中"先召回再精排"的同构设计。

相比 DeerFlow 的 `read_file` 一次性加载全文，当前设计在 skill 数量多时有显著的 token 节省优势：

```
假设 20 个 Skill，每个 SKILL.md 平均 1000 token：

DeerFlow 方式（全量注入摘要 + 按需 read_file）：
  摘要: ~400 token + 命中后全文: ~1000 token = ~1400 token

当前方式（框架 list_skills + 按需 load_skill）：
  list_skills: ~200 token + 命中后 load_skill: ~1000 token = ~1200 token
  且 list_skills 返回结构化 XML，LLM 解析更准确
```

## 五、完整执行流程

```
用户查询
    │
    ▼
┌──────────────────────────────────────┐
│  主 Agent (System Prompt)             │
│  ├─ 框架自动注入 skill 摘要           │  ← SkillsToolset.get_instructions()
│  ├─ skill_routing.md 路由引导         │  ← 自研
│  ├─ Base Tool 描述 (分组 dict)        │
│  └─ MCP Tool 描述                     │
└──────────┬───────────────────────────┘
           │
           │  Agent 调用 list_skills() 判断是否需要 skill
           │
     ┌─────▼──────┐
     │ load_skill  │  ← 框架工具，按需加载完整 SKILL.md
     └─────┬──────┘
           │
     ┌─────▼──────────────────────────────────┐
     │  根据 execution 模式分流                 │
     │                                         │
     │  native:                                │
     │    Agent 按 SKILL.md 指引               │
     │    → 调用 Base Tool / MCP Tool 执行      │
     │    → read_skill_resource() 按需读资源    │
     │                                         │
     │  sandbox:                               │
     │    简单脚本 → run_skill_script()         │  ← 框架 subprocess
     │    复杂脚本 → execute_skill()            │  ← Pi Agent 智能执行
     └────────────────────────────────────────┘
```

## 六、设计原则总结

| 设计原则 | 在当前架构中的体现 |
|---------|-----------------|
| 分层执行 (Tiered Execution) | `run_skill_script` (轻量) + Pi Agent (智能) |
| 声明式分流 (Convention over Config) | `execution: native \| sandbox` |
| 最小权限 (Least Privilege) | sandbox skill 隔离执行 |
| 开闭原则 (Open-Closed) | MCP 协议扩展工具，不改代码 |
| 核心域/支撑域 (DDD) | Pi Agent 自研 + 框架复用通用能力 |
| 信息觅食 (Information Foraging) | 三阶段渐进式加载 |
| 有界理性 (Bounded Rationality) | 全量工具 + 角色指令引导 |

核心优势：**既不像 DeerFlow 那样完全放弃沙箱隔离和智能执行，也不像重构前的设计那样把所有 skill 都扔进沙箱断了和 base tool 的连接**。通过声明式分流，让每个 skill 走最适合它的执行路径。

## 参考文献

- Wooldridge, M. (2009). *An Introduction to MultiAgent Systems*. Wiley. — Cognitive Agent 概念
- Evans, E. (2003). *Domain-Driven Design*. Addison-Wesley. — 核心域/支撑域划分
- Simon, H. (1957). *Models of Man*. Wiley. — Bounded Rationality
- Pirolli, P. & Card, S. (1999). Information Foraging. *Psychological Review*. — Information Scent
- Schick, T. et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS*. — 工具数量与 LLM 决策质量
