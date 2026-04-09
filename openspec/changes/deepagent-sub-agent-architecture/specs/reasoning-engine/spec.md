## ADDED Requirements

### Requirement: 复杂度评估

ReasoningEngine SHALL 对用户输入进行五维度复杂度评估，输出 ComplexityScore（level + score + dimensions + suggested_mode）。

五个维度及权重：
- task_count（0.25）：通过动词和连接词数量估算隐含子任务数
- domain_span（0.20）：检测不同领域关键词共现程度
- dependency_depth（0.20）：顺序连接词（先…再…然后…最后）的层级深度
- output_complexity（0.15）：输出类型复杂度（报告 > 图表 > 列表 > 单值）
- reasoning_depth（0.20）：推理类型深度（对比分析 > 综合 > 检索 > 直答）

加权求和得到 score（0.0~1.0），映射到 ComplexityLevel：
- LOW（< 0.25）→ DIRECT
- MEDIUM（0.25~0.50）→ AUTO
- HIGH（0.50~0.75）→ SUB_AGENT
- VERY_HIGH（> 0.75）→ SUB_AGENT

#### Scenario: 简单问题评估为 LOW
- **WHEN** 用户输入 "今天天气怎么样"
- **THEN** 复杂度评估返回 ComplexityLevel.LOW，suggested_mode 为 DIRECT

#### Scenario: 多步骤任务评估为 HIGH
- **WHEN** 用户输入 "搜索最近的AI论文，分析趋势，生成可视化报告"
- **THEN** 复杂度评估返回 ComplexityLevel.HIGH，suggested_mode 为 SUB_AGENT

#### Scenario: 模糊区间触发 LLM 兜底
- **WHEN** 规则评估 score 在 0.35~0.55 区间
- **THEN** ReasoningEngine SHALL 调用 fast_model 进行二次分类判断

### Requirement: 执行模式决策

ReasoningEngine SHALL 通过三级分类策略决定执行模式（ExecutionMode）。

- Level 0：用户通过 mode 参数显式指定（direct/auto/plan_and_execute/sub_agent）→ 直通
- Level 1：规则匹配（零延迟），中英文正则模式匹配
- Level 2：复杂度评估（五维度加权 + LLM 兜底）

Level 1 匹配到 plan 模式后，SHALL 进一步评估复杂度，HIGH/VERY_HIGH 升级为 SUB_AGENT。

#### Scenario: 用户显式指定模式
- **WHEN** 用户请求 mode="sub_agent"
- **THEN** ReasoningEngine 直接返回 ExecutionMode.SUB_AGENT，不执行规则匹配和复杂度评估

#### Scenario: 规则匹配到 DIRECT
- **WHEN** 用户输入 "写一个快速排序算法"
- **THEN** 匹配中文 direct 模式（写+代码），返回 ExecutionMode.DIRECT

#### Scenario: plan 模式升级为 SUB_AGENT
- **WHEN** 用户输入 "先搜索三个竞品的技术架构，然后对比分析，最后生成评估报告"
- **THEN** Level 1 匹配到 plan 模式，复杂度评估为 HIGH，最终返回 ExecutionMode.SUB_AGENT

### Requirement: 工具资源一次获取

ReasoningEngine.decide() SHALL 在决策阶段一次性获取所有工具资源（Workers/MCP/Skills/桥接工具），封装为 ResolvedResources，整个请求生命周期内共享。

MCP toolsets 的网络连接 SHALL 只建立一次，通过 ResolvedResources 向下传递给主 Agent 和所有 Sub-Agent。

#### Scenario: MCP 连接复用
- **WHEN** 一个 SUB_AGENT 模式请求创建了 3 个并行 Sub-Agent
- **THEN** MCP 连接只建立 1 次，3 个 Sub-Agent 通过桥接工具共享同一批资源

#### Scenario: 资源获取失败降级
- **WHEN** MCP 连接失败
- **THEN** ResolvedResources.mcp_toolsets 为空列表，Agent 继续执行但无 MCP 工具可用

### Requirement: 执行计划输出

ReasoningEngine.decide() SHALL 返回 ExecutionPlan，包含 mode、complexity、prompt_prefix、resources 四个字段。

不同模式的 prompt_prefix：
- DIRECT：空字符串
- AUTO：空字符串
- PLAN_AND_EXECUTE：注入 DAG 规划指令
- SUB_AGENT：注入 Sub-Agent 使用说明和可用角色列表

#### Scenario: SUB_AGENT 模式的 ExecutionPlan
- **WHEN** 复杂度评估为 HIGH
- **THEN** ExecutionPlan.mode 为 SUB_AGENT，prompt_prefix 包含可用 Sub-Agent 角色描述，resources 包含已获取的桥接工具
