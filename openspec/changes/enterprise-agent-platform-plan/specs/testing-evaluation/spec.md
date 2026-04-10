## ADDED Requirements

### Requirement: pytest 测试框架
系统 SHALL 使用 pytest 作为测试框架，配置 conftest.py 提供通用 fixtures（mock_llm、mock_redis、test_session、sandbox_container）。测试 SHALL 集成到 CI Pipeline，PR 合并前必须通过。

#### Scenario: CI 集成
- **WHEN** 提交 PR
- **THEN** CI SHALL 自动运行全部测试，失败则阻止合并

#### Scenario: 测试隔离
- **WHEN** 运行测试套件
- **THEN** 每个测试用例 SHALL 使用独立的 session 和临时数据，测试间无状态泄漏

### Requirement: Runtime 核心路径单元测试
系统 SHALL 覆盖以下核心路径的单元测试：ReasoningEngine 复杂度评估、模式路由、Agent Factory 构建、Middleware Pipeline 各 stage、Context Manager 模板组装。

#### Scenario: 复杂度评估测试
- **WHEN** 输入 "1+1等于几"
- **THEN** 复杂度分数 SHALL < 0.35，模式 SHALL 为 DIRECT

#### Scenario: 模式升级测试
- **WHEN** DIRECT 模式返回空输出
- **THEN** 系统 SHALL 升级到 AUTO 模式

#### Scenario: Middleware 短路测试
- **WHEN** PermissionCheck 拒绝请求
- **THEN** 后续 stage SHALL 不执行

### Requirement: Sandbox 隔离验证测试
系统 SHALL 验证沙箱的安全隔离性：网络隔离、文件系统隔离、进程隔离、资源限制。

#### Scenario: 网络隔离验证
- **WHEN** NONE 策略沙箱尝试访问外部网络
- **THEN** 请求 SHALL 被拒绝，测试验证无网络泄漏

#### Scenario: 文件系统隔离验证
- **WHEN** 沙箱尝试访问宿主文件系统
- **THEN** 访问 SHALL 被拒绝，测试验证路径隔离

#### Scenario: 资源限制验证
- **WHEN** 沙箱内进程消耗内存超过限制
- **THEN** 进程 SHALL 被 OOM Kill，测试验证资源限制生效

### Requirement: API Contract 测试
系统 SHALL 对所有 REST API 端点进行 contract 测试，验证请求/响应格式符合 OpenAPI Schema。

#### Scenario: 请求格式验证
- **WHEN** 客户端发送不符合 Schema 的请求
- **THEN** 系统 SHALL 返回 422 Validation Error，包含具体字段错误

#### Scenario: 响应格式验证
- **WHEN** API 返回响应
- **THEN** 响应 SHALL 符合 OpenAPI Schema 定义的格式

### Requirement: 全链路集成测试
系统 SHALL 实现端到端集成测试，覆盖完整请求链路：API → ReasoningEngine → Agent → Worker → 响应。

#### Scenario: 简单查询全链路
- **WHEN** POST /api/agent/query {"query": "1+1等于几"}
- **THEN** 系统 SHALL 返回正确答案，全链路耗时 < 5 秒

#### Scenario: 工具调用全链路
- **WHEN** POST /api/agent/query {"query": "搜索最新AI论文"}
- **THEN** 系统 SHALL 调用搜索工具并返回结果，验证工具调用链完整

### Requirement: Agent Evaluation 系统
系统 SHALL 实现 Agent 质量评估系统，评估维度包括：回答准确率、工具调用合理性、响应质量（完整性/相关性/格式）、响应时间。

#### Scenario: 基准测试集
- **WHEN** 运行 Evaluation
- **THEN** 系统 SHALL 对预定义的测试集（100+ 用例）逐一执行，统计各维度得分

#### Scenario: 回归检测
- **WHEN** 代码变更后运行 Evaluation
- **THEN** 系统 SHALL 对比前后得分，得分下降超过 5% 时标记为回归

#### Scenario: 工具调用合理性
- **WHEN** 评估 Agent 的工具调用
- **THEN** 系统 SHALL 检查：是否调用了正确的工具、参数是否合理、是否有冗余调用

### Requirement: 性能基准测试
系统 SHALL 建立性能基准，覆盖：冷启动时间、首 token 延迟、端到端延迟（P50/P95/P99）、并发吞吐量。

#### Scenario: 基准建立
- **WHEN** 首次运行性能测试
- **THEN** 系统 SHALL 记录各指标基准值

#### Scenario: 性能回归检测
- **WHEN** 代码变更后运行性能测试
- **THEN** 指标恶化超过 20% 时 SHALL 标记为性能回归
