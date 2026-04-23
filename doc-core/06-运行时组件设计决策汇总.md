# Super-Agent 运行时架构设计决策汇总

## 一、文档定位

本文用于汇总以下 6 份运行时相关分析文档的核心结论、问题、约束与处理措施，形成一份可供架构评审、方案回顾和后续实施参考的统一文档：

- `component-doc/agent-execution-engine-comparison.md`
- `component-doc/hooks-and-middleware-analysis.md`
- `component-doc/mcp-architecture-design.md`
- `component-doc/skill-system-design-analysis.md`
- `component-doc/toolset-analysis-and-reuse-decision.md`
- `function-compare-summary/multi-model-architecture-plan.md`

本文不按原文逐篇拼接，而按运行时架构的决策主题归类整理。

---

## 二、总体结论

当前运行时架构的核心方向已经比较清晰，可以概括为 6 条结论：

1. **沙箱执行引擎继续以 Pi-mono 为主**
   - Claude API 直调可以作为轻量补充，但不适合作为主替代方案
   - Claude Code CLI 成本和上下文开销过高，不适合当前场景

2. **多模型体系必须从“模型名猜测 + 业务层特判”升级为“配置驱动 + 能力建模 + Provider 适配层”**
   - 业务层只依赖逻辑角色，不直接依赖 provider 细节
   - 运行时差异统一下沉到模型注册表、兼容层和运行时策略层

3. **Hooks、Capabilities、Toolset 三者不是替代关系，而是分层分责关系**
   - Hooks 负责轻量观察、拦截、审计
   - Capabilities 负责深层行为注入、状态隔离、Prompt/工具动态控制
   - Toolset 负责工具组织、包装、过滤和统一观测

4. **Skill 与 MCP 都应视为“外部能力接入层”，但两者边界不同**
   - MCP 解决外部服务能力接入
   - Skill 解决知识模板、脚本执行和执行路径分流

5. **框架原生能力应优先复用，但要保留少量关键自研薄层**
   - 优先复用 pydantic-deep / pydantic-ai / fastmcp 原生能力
   - 仅在框架缺口处自建管理层、适配层和策略层

6. **当前最合理的演进方式是渐进式改造，不是一次性重写**
   - 先抽配置与注册表
   - 再收口运行时策略
   - 再统一 Toolset/Hook/Capability 职责
   - 最后再看是否值得继续深度框架化

---

## 三、文档归类总览

| 专题 | 对应文档 | 核心问题 | 汇总结论 |
|------|----------|----------|----------|
| 执行内核选型 | `agent-execution-engine-comparison.md` | 沙箱执行引擎选谁 | 继续以 Pi-mono 为主 |
| 多模型架构 | `multi-model-architecture-plan.md` | 当前多模型体系为什么不可持续，怎么改 | 引入 catalog / provider / registry / compatibility 分层 |
| Hook 与行为注入 | `hooks-and-middleware-analysis.md` | Hooks、Capabilities、Middleware 如何分工 | Hook 做轻拦截，Capability 做深控制 |
| Toolset 复用边界 | `toolset-analysis-and-reuse-decision.md` | Base tools 是否要全面迁移到 FunctionToolset | 暂不全面迁移，组装层优先复用 |
| MCP 接入架构 | `mcp-architecture-design.md` | MCP 为什么不能只靠框架原生 | 在原生之上增加管理层与参数注入层 |
| Skill 体系设计 | `skill-system-design-analysis.md` | Skill 如何在知识模板、脚本执行、沙箱之间平衡 | 声明式分流 + 分层执行 |

---

## 四、专题一：执行内核与模型体系

### 4.1 执行引擎选型结论

针对沙箱执行引擎，核心结论是：

- **主方案：Pi-mono CLI**
- **补充方案：Claude API 直调**
- **不建议作为主方案：Claude Code CLI**

原因如下：

- Pi-mono 在功能完整度上明显更成熟，具备完整 agent loop、工具执行、上下文压缩、session、hooks 等能力
- Claude API 直调虽然性能接近，但当前只适合作为“轻量、不需要完整沙箱控制”的补充方案
- Claude Code CLI 内置上下文过重，成本和时延都明显偏高

最终决策不是“谁 benchmark 更快一点”，而是“谁在生产场景中综合性价比更高”。在这一点上，Pi-mono 目前仍然最合适。

### 4.2 多模型架构的主要问题

`multi-model-architecture-plan.md` 不是一篇单纯的目标架构文档，它首先指出了当前多模型体系存在的一组基础性问题：

1. `settings.py` 只支持少量固定字段
   - 模型角色增加时需要不断扩展配置字段
   - 不适合多 provider、多角色、多档位路由

2. provider 判断依赖模型名猜测
   - 例如用 `"claude" in model_name.lower()` 判断是否走 Anthropic 原生路径
   - 这会导致模型接入越来越脆弱

3. 模型能力差异没有统一建模
   - streaming、tool calling、reasoning、reasoning_content 要求等都散落在业务层

4. provider-specific settings 泄漏到业务/API 层
   - 例如网关/API 层直接处理 Claude thinking 配置
   - 这意味着每增加一类模型就要继续堆条件分支

5. 逻辑角色与模型绑定过死
   - orchestrator / subagent / classifier 粒度太粗
   - 后续难以扩展 planner、fast_router、sandbox_pi 等更细角色

### 4.3 框架与工程层面的约束

多模型问题不只是“配置不优雅”，还受限于当前调用链和框架使用方式：

- 业务代码直接依赖 `get_model("orchestrator")` 这类简化入口，角色分辨率不足
- 网关层目前承担了部分 provider 差异处理，导致路由层与模型层耦合
- thinking / tool calling 差异没有在协议兼容层统一收口
- 当前的模型使用点分散在 orchestrator、sub-agent、planner、gateway 等多个位置，改造时必须兼顾兼容性

### 4.4 处理措施

针对上述问题，建议的处理措施是引入分层多模型架构：

1. **Catalog 层**
   - 管理 provider、model profile、role binding
   - 配置以 `models.yaml` 为主，secret 仍通过环境变量注入

2. **Provider 适配层**
   - 把 `ModelProfile` 转换为真正可执行的模型对象
   - 隔离 OpenAI-compatible、Anthropic-native 等差异

3. **Registry / Facade 层**
   - 对外暴露 role-based 查询入口
   - 例如 `get_model_bundle(role, execution_mode)`

4. **Runtime Policy 层**
   - 根据 execution mode 与 model capability 统一生成运行时策略
   - 包括 thinking、tool calling、streaming、compatibility 注入等

5. **Compatibility 层**
   - 统一处理 reasoning_content、transport、tool call 兼容差异
   - 业务层不再关注 Kimi/Qwen/Claude 的特例

### 4.5 该专题的统一结论

多模型问题的本质不是“如何新增一个模型”，而是“如何让业务层彻底不感知模型提供方差异”。  
因此最终目标应是：

- 业务层只依赖逻辑角色
- provider 差异进入适配层
- 能力差异进入 capability / compatibility 建模
- 运行时策略由 runtime policy 统一收口

---

## 五、专题二：Hook、Capability 与 Toolset 的职责划分

### 5.1 Hooks / Capabilities / Middleware 的关系

从框架演进看，三者关系已经很清楚：

- Middleware 是旧概念，已逐步被 Capability 取代
- Capability 是当前的底层行为注入单元
- Hook 是 Capability 的简化用户接口

因此应该避免把这三者当成同层替代物。更合理的理解是：

- **Hook：轻量事件驱动层**
- **Capability：深度行为注入层**
- **Toolset：工具组织与包装层**

### 5.2 Hook 适合做什么

Hook 更适合做简单横切关注点：

- 循环检测
- 工具调用审计
- 危险操作拦截
- 工具结果脱敏
- 事件推送
- 错误告警

它的特点是：

- 逻辑轻
- 以观察和拦截为主
- 不负责改变 Agent 的总体执行结构

### 5.3 Capability 适合做什么

Capability 适合做深度控制类能力：

- 动态工具过滤
- Prompt 注入
- Token 预算管控
- 状态隔离
- 包装 model request / tool execute
- 自定义工具集注入
- 多租户隔离

它的特点是：

- 能接触完整执行上下文
- 能包装执行流
- 能管理 run 级状态

### 5.4 Toolset 适合做什么

Toolset 负责的是工具层组织和包装，而不是简单事件通知：

- 工具注册
- 工具合并
- 工具过滤
- 工具命名空间控制
- 统一包装观测逻辑
- 统一处理工具 schema 和 call_tool

因此 Toolset 最适合承载：

- Langfuse span 包装
- 工具结果发布
- 错误格式统一
- MCP / Skill / Base Tools 的统一组装

### 5.5 当前实现的主要问题

当前实现里，三层机制有一些职责混叠：

1. 事件推送没有完全落到 Hook/Toolset 层，仍有部分逻辑在 `rest_api` 中硬编码
2. Token Tracker 仍是占位逻辑，没有真正收口
3. `_wrap_with_tool_result`、Hooks、Toolset wrapper 三套机制并存，存在重复职责
4. FastAPI 中间件层较薄，请求级横切能力还不完整

### 5.6 该专题的统一结论

正确的分工应当是：

- **FastAPI Middleware**：处理 HTTP 请求级能力
- **Capability**：处理 Agent 级深层控制
- **Hook**：处理轻量事件拦截与观察
- **Toolset**：处理工具组织、包装与统一观测

其中最重要的原则是：

- Hook 做观察者
- Capability 做深控制
- Toolset 做参与者与包装器

---

## 六、专题三：Toolset 复用边界与 Base Tools 策略

### 6.1 是否应将 Base Tools 全量迁移到 FunctionToolset

分析结论是：**当前阶段不建议**。

原因不是 FunctionToolset 不好，而是当前工程上下文下，全面迁移的成本与收益不匹配。

### 6.2 主要约束

关键约束来自当前 deps 体系：

- Base Tools 当前通过闭包捕获 `workers`
- 如果改为 FunctionToolset 风格，就要把 `workers` 放进 `ctx.deps`
- 但当前 `DeepAgentDeps` 扩展成本高，且对子 Agent clone 链路不友好

这意味着：

- 完整迁移需要同时解决 deps 扩展、sub-agent 继承、上下文兼容等问题
- 改造面较大，且不会带来等比例收益

### 6.3 为什么暂不迁移是合理的

当前闭包式 base tools 方案有几个现实优势：

- 直接、稳定
- 对测试友好
- 对 sub-agent 天然兼容
- 当前 9 个工具规模还没达到必须重构的程度

更关键的是，从运行结果看：

- 当前“闭包函数列表”最终仍然会进入框架的工具包装链路
- 显式改成 FunctionToolset 只是组织形式变化，不是能力质变

### 6.4 可以优先复用的部分

虽然不建议全量迁移，但组装层完全可以复用框架能力：

1. `WrapperToolset`
   - 用于替代逐函数 `_wrap_with_tool_result`

2. `filtered()`
   - 用于声明式过滤工具

3. `defer_loading()`
   - 用于延迟加载 MCP 工具

4. `CombinedToolset`
   - 用于统一工具集组合和冲突检测

### 6.5 该专题的统一结论

Base Tools 的策略应是：

- **短期：保持闭包方案**
- **中期：在组装层优先引入 Toolset Wrapper**
- **远期：等 deps 机制更成熟后再评估完整 Toolset 化**

这是一种“局部框架化，而不是强行全面框架化”的策略。

---

## 七、专题四：MCP 接入架构

### 7.1 MCP 方案的核心判断

MCP 接入不应该完全自己重写，也不能只裸用框架原生能力。  
最合理的方式是：

- **底层复用 fastmcp / pydantic-ai 原生能力**
- **上层增加一层轻量管理层**

### 7.2 当前设计为什么合理

当前方案的设计思路是：

- 协议通信：完全复用 fastmcp transport
- 工具发现与 schema：完全复用 FastMCPToolset
- 命名空间：复用 PrefixedToolset
- 上层只新增：
  - `MCPClientManager`
  - `DefaultArgsToolset`

这两个新增组件分别补齐了框架原生的关键缺口：

1. **MCPClientManager**
   - 多端点配置
   - 生命周期独立管理
   - 缓存与刷新
   - 环境变量驱动

2. **DefaultArgsToolset**
   - 默认参数注入
   - schema 字段隐藏
   - 解决第三方 MCP 服务把认证参数暴露为调用参数的问题

### 7.3 为什么不能只用框架原生 MCP Capability

原生方式的几个限制包括：

- 协议识别依赖 URL 推断，不够稳
- 缺少 default_args 注入能力
- 生命周期绑定 Agent，请求间不共享
- 缺少定期刷新与手动刷新管理层
- 运维配置不够灵活

### 7.4 该专题的统一结论

MCP 架构的最佳实践不是“推翻原生能力重做”，而是：

- 保持底层完全复用
- 只在配置、生命周期、参数注入、缓存刷新四个点做增强

这是典型的“薄封装”设计，维护成本最低，收益也最明确。

---

## 八、专题五：Skill 系统设计

### 8.1 Skill 的定位

Skill 在当前体系中不应被理解成单纯的 prompt 模板，也不应被理解成单纯的脚本包，而应定义为：

- **知识模板 + 执行包**

它既可能只是知识注入，也可能最终落到脚本执行、沙箱执行或外部工具调用。

### 8.2 当前设计的关键决策

Skill 系统的几个关键设计决策是：

1. **声明式分流**
   - 通过 `execution: native | sandbox` 决定执行路径

2. **分层执行**
   - 简单脚本：走轻量脚本执行
   - 复杂脚本：走 Pi Agent 智能执行

3. **渐进式加载**
   - skill 摘要 → 全文 → 资源/脚本
   - 避免全量注入导致 token 浪费

4. **与 MCP 深度协同**
   - native skill 可调用 base tools / MCP tools
   - sandbox skill 可通过隔离环境完成复杂执行

### 8.3 与 DeerFlow / pydantic-deep 的差异

与 DeerFlow 相比，当前设计没有把 Skill 简化为 bash 盲执行，而是保留了智能执行能力与安全分流。  
与 pydantic-deep 原生相比，当前设计不是完全自研，而是：

- 复用 SkillsToolset、SkillsDirectory、LocalSkillScriptExecutor 等通用能力
- 保留 Pi Agent、动态创建 Skill、分流策略等差异化能力

### 8.4 该专题的统一结论

Skill 系统的正确设计不是“全 native”或“全 sandbox”，而是：

- **知识与执行解耦**
- **执行路径声明式分流**
- **轻脚本与重脚本分层执行**
- **通用能力框架复用，差异化执行能力自研保留**

---

## 九、统一设计原则

从这 6 份文档中，可以提炼出一套一致的运行时架构原则：

1. **优先复用原生框架能力**
   - fastmcp、pydantic-ai、pydantic-deep 提供的底层能力应优先复用

2. **只在框架缺口处做薄封装**
   - 不重造协议层，不重造工具发现层
   - 只补配置、生命周期、兼容性和治理能力

3. **核心差异化能力保留自研**
   - Pi Agent 智能执行
   - Skill 执行分流
   - 多模型兼容策略

4. **配置驱动优于硬编码**
   - Provider、Model、Role、MCP 端点、默认参数都应配置化

5. **运行时策略应集中收口**
   - 不能把 provider/model 差异散落在 gateway、orchestrator、agent_factory 中

6. **生命周期尽量独立于单次 Agent Run**
   - 例如 MCP 连接、资源缓存、模型注册表，都应支持请求间复用

7. **分层而不是堆叠**
   - Hook、Capability、Toolset、Provider、Registry 各自承担明确职责

8. **渐进式演进优于一次性重构**
   - 先抽象，再收口，再替换，不做大爆炸式改造

---

## 十、建议的汇总架构视图

```text
┌─────────────────────────────────────────────┐
│ Gateway / API Layer                         │
│ REST / SSE / WebSocket                      │
├─────────────────────────────────────────────┤
│ Orchestrator Layer                          │
│ ReasoningEngine / AgentFactory / Planning   │
├─────────────────────────────────────────────┤
│ Runtime Governance Layer                    │
│ Hooks / Capabilities / Toolset Wrappers     │
├─────────────────────────────────────────────┤
│ Model Runtime Layer                         │
│ Catalog / Registry / Runtime / Compatibility│
├─────────────────────────────────────────────┤
│ Capability Access Layer                     │
│ Base Tools / Skill / MCP / Sandbox          │
├─────────────────────────────────────────────┤
│ Execution Kernel Layer                      │
│ Pi-mono / Lightweight Script Executor       │
└─────────────────────────────────────────────┘
```

这个分层对应的核心决策是：

- 执行引擎以 Pi-mono 为主
- 多模型差异在模型运行时层收口
- Hook / Capability / Toolset 在治理层分责
- Skill / MCP / Sandbox 作为能力接入层并列存在

---

## 十一、后续实施建议

如果按实施顺序推进，建议分为四步：

1. **先做多模型注册表收口**
   - 建立 `models.yaml`
   - 引入 catalog / registry / provider 结构

2. **再收口运行时策略**
   - 去掉 gateway/API 层中的 provider 特判
   - 统一 thinking / tool calling / compatibility 处理

3. **再统一工具治理链路**
   - 用 Toolset Wrapper 替代部分 `_wrap_with_tool_result`
   - 让 Hook、Capability、Toolset 职责更清晰

4. **最后再优化 Skill / MCP / Sandbox 的组合体验**
   - 包括渐进加载、统一事件推送、统一观测与更细粒度执行分流

---

## 十二、原始文档索引

| 文档 | 用途 |
|------|------|
| `component-doc/agent-execution-engine-comparison.md` | 沙箱执行引擎选型与 benchmark 结论 |
| `function-compare-summary/multi-model-architecture-plan.md` | 多模型体系的问题、约束与改造方案 |
| `component-doc/hooks-and-middleware-analysis.md` | Hook / Capability / Middleware 的职责分析 |
| `component-doc/toolset-analysis-and-reuse-decision.md` | Toolset 复用边界与 Base Tools 策略 |
| `component-doc/mcp-architecture-design.md` | MCP 接入增强层设计 |
| `component-doc/skill-system-design-analysis.md` | Skill 体系与执行分流设计 |

## 十三、结论

这 6 份文档并不是同一个子系统的重复说明，而是从不同侧面共同构成了 Super-Agent 的运行时架构决策集。  
最适合的整理方式不是逐篇摘要，而是按“执行内核、模型体系、行为治理、能力接入、设计原则”五个维度进行归纳。

这份汇总文档的价值在于：

- 把原本分散的技术决策串成一套完整逻辑
- 让后续实现和架构评审有统一语义
- 为后续继续演进提供清晰的边界与优先级
