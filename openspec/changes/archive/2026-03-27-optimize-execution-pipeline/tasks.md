## 1. 数据模型变更

- [x] 1.1 在 `src/schemas/api.py` 中修改 `QueryRequest.mode` 的 pattern，从 `^(auto|plan_and_execute|react|direct)$` 改为 `^(auto|plan_and_execute|direct)$`

## 2. IntentRouter 实现

- [x] 2.1 创建 `src/orchestrator/intent_router.py`，定义 `ExecutionMode` 枚举（DIRECT / AUTO / PLAN_AND_EXECUTE）
- [x] 2.2 在 `intent_router.py` 中实现 `IntentRouter.classify()` 方法：Level 0 显式 mode 直通 + Level 1 规则匹配（中英文触发词）+ Level 2 默认 auto
- [x] 2.3 在 `intent_router.py` 中实现分类结果结构化日志（query 截断、input_mode、resolved_mode、match_level）

## 3. ToolSetAssembler 实现

- [x] 3.1 创建 `src/orchestrator/toolset_assembler.py`，定义 `AssembleResult` 数据类（tool_filter、prompt_prefix、agent_override）
- [x] 3.2 在 `toolset_assembler.py` 中实现 `ToolSetAssembler.assemble()` 方法：direct 模式过滤规划工具、auto 模式全量、plan_and_execute 模式全量 + prompt_prefix
- [x] 3.3 在 `toolset_assembler.py` 中实现 direct 模式的 Agent 实例创建（lazy 初始化，共享 model 配置，排除 plan_and_decompose/list_available_skills/create_new_skill 工具）

## 4. Orchestrator 重构

- [x] 4.1 在 `src/orchestrator/orchestrator_agent.py` 中实现 `_execute_agent()` 统一执行函数（MCP fallback、工具过滤、prompt_prefix 注入、token usage 更新、A2UI 帧注入、历史保存）
- [x] 4.2 重构 `run_orchestrator()` 为三阶段管道：IntentRouter.classify → ToolSetAssembler.assemble → _execute_agent
- [x] 4.3 移除旧代码：`_classify_intent`、`_make_direct_fn`、`_make_react_fn`、`_make_plan_execute_fn` 四个函数

## 5. System Prompt 简化

- [x] 5.1 修改 `src/orchestrator/prompts/system.py`，移除"简单任务直通规则"和"复杂度判断"段落（由 IntentRouter 承担）
- [x] 5.2 修改 `src/orchestrator/prompts/planning.py`，保留"最小任务原则"和反面示例（plan_and_execute 模式仍需要）

## 6. 测试

- [x] 6.1 编写 `tests/test_intent_router.py`，测试显式 mode 直通、中文规则匹配（代码/搜索/多步骤）、英文规则匹配、模糊意图返回 auto
- [x] 6.2 编写 `tests/test_toolset_assembler.py`，测试 direct 模式工具过滤、auto 模式全量、plan_and_execute 的 prompt_prefix、direct Agent 实例 lazy 初始化
- [x] 6.3 编写 `tests/test_execution_pipeline.py`，测试三阶段管道端到端流程（mock Agent），验证 direct 模式不调 plan_and_decompose、plan_and_execute 模式注入 prefix
