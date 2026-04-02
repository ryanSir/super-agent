### Requirement: IntentRouter 分类接口
系统 SHALL 提供 `IntentRouter` 类，接收用户 query 和 mode 参数，返回 `ExecutionMode` 枚举值（`direct` / `auto` / `plan_and_execute`）。MUST 位于 `src/orchestrator/intent_router.py`。

#### Scenario: 用户显式指定 mode
- **WHEN** 用户请求 `mode="direct"`
- **THEN** IntentRouter 直接返回 `ExecutionMode.DIRECT`，不执行任何分类逻辑

#### Scenario: 用户显式指定 plan_and_execute
- **WHEN** 用户请求 `mode="plan_and_execute"`
- **THEN** IntentRouter 直接返回 `ExecutionMode.PLAN_AND_EXECUTE`

### Requirement: 规则优先分类（Level 1）
当 `mode="auto"` 时，IntentRouter MUST 先执行规则匹配。规则匹配 MUST 零延迟（不调用 LLM）。

规则定义：
- `direct` 触发：单一动作动词 + 明确对象（"写/实现/编写/生成 + 代码/算法/脚本/程序"、"搜索/检索/查找 + 论文/专利/文献"、"翻译/总结/解释"）
- `plan_and_execute` 触发：多步骤连接词（"并且/然后/接着/同时"、"先...再...最后"、"对比...分析...生成"、"检索...并...可视化"）
- 未匹配任何规则 → 返回 `auto`

#### Scenario: 简单代码任务匹配 direct
- **WHEN** query = "用 Python 写一个快速排序算法"，mode = "auto"
- **THEN** 规则匹配命中 "写 + 算法"，返回 `ExecutionMode.DIRECT`

#### Scenario: 简单搜索任务匹配 direct
- **WHEN** query = "搜索 AI 相关论文"，mode = "auto"
- **THEN** 规则匹配命中 "搜索 + 论文"，返回 `ExecutionMode.DIRECT`

#### Scenario: 多步骤任务匹配 plan_and_execute
- **WHEN** query = "检索近三个月的 AI 专利，分析趋势，并用图表展示"，mode = "auto"
- **THEN** 规则匹配命中 "检索...分析...展示" 多步骤模式，返回 `ExecutionMode.PLAN_AND_EXECUTE`

#### Scenario: 模糊意图返回 auto
- **WHEN** query = "帮我看看这个数据有什么问题"，mode = "auto"
- **THEN** 未匹配任何规则，返回 `ExecutionMode.AUTO`

#### Scenario: 英文查询匹配
- **WHEN** query = "Write a Python script to sort numbers"，mode = "auto"
- **THEN** 规则匹配命中 "write + script"，返回 `ExecutionMode.DIRECT`

### Requirement: ExecutionMode 枚举
系统 SHALL 定义 `ExecutionMode` 枚举，包含三个值：`DIRECT`、`AUTO`、`PLAN_AND_EXECUTE`。

#### Scenario: 枚举值与 QueryRequest.mode 对应
- **WHEN** `QueryRequest.mode = "direct"`
- **THEN** 对应 `ExecutionMode.DIRECT`

### Requirement: 分类结果日志
IntentRouter MUST 在每次分类后记录结构化日志，包含 `query`（截断至 100 字符）、`input_mode`、`resolved_mode`、`match_level`（"explicit" / "rule" / "default"）。

#### Scenario: 规则匹配日志
- **WHEN** 规则匹配命中 direct
- **THEN** 日志输出 `[IntentRouter] 分类完成 | query=写个快排... input_mode=auto resolved_mode=direct match_level=rule`
