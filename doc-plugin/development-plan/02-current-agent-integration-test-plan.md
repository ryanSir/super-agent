# 02. 当前 Agent 集成测试计划

## 目标

当前仓库本身已经是一个 Agent 项目。Plugin 功能开发完成后，不能只用 `plugin-poc` CLI 验证，而应接入当前 `src_deepagent`，做真实 Agent 集成测试。

集成测试要验证：

- Agent 能发现 Plugin 提供的能力。
- Agent 能把 Skill context 合并到自身上下文。
- Agent 能通过 Plugin Core API 调用工具。
- Plugin 调用能跑通主链路；权限、凭据、审计和观测第一阶段可以先用占位实现，后续再补完整治理。
- Plugin 能力不会破坏当前 Agent 的执行模式、流式输出和安全边界。

## 当前 Agent 相关模块

| 当前模块 | 现有职责 | Plugin 集成关注点 |
| --- | --- | --- |
| `src_deepagent/capabilities/registry.py` | 汇总 base tools、skills、MCP | 增加 Plugin capability provider，或从 Plugin Core API 拉取能力 |
| `src_deepagent/orchestrator/reasoning_engine.py` | 决策执行模式、获取资源、构建上下文 | 在资源解析阶段加入 Plugin skill summary 和 tool names |
| `src_deepagent/orchestrator/agent_factory.py` | 创建主 Agent 和 sub-agent | 将 Plugin tool wrapper 注入 Agent tools |
| `src_deepagent/gateway/rest_api.py` | `/api/agent/query` 和 SSE 网关 | 集成测试入口，验证用户请求到插件调用的完整链路 |
| `src_deepagent/security/` | 权限、审计、注入防护、安全策略 | 对齐 Plugin Policy / Credential / Audit |
| `src_deepagent/monitoring/` | Langfuse、metrics、pipeline events | 对齐 Plugin invocation trace 和 audit |

## 建议集成方式

第一阶段建议采用“Plugin Core API provider”方式，而不是把 Plugin 管理和调用逻辑直接塞进 Agent Runtime。

```text
src_deepagent
  -> PluginCapabilityProvider
  -> Plugin Core API
     -> Capability Discovery
     -> Skill Context
     -> Tool Invocation
     -> Policy / Credential / Audit
```

这样可以保持边界：

- Agent 负责理解任务、选择能力、组织结果。
- Plugin Core 负责能力治理、凭据、权限和调用。
- 当前 Agent 不直接接触插件密钥和内部实现。

## 最小集成测试场景

### 场景 1：能力发现

准备：

- 安装并启用一个测试插件。
- 插件暴露一个简单 tool，例如 `send_message` 或 `lookup_demo_record`。

验证：

- `src_deepagent` 启动后能通过 provider 拉取能力。
- Agent prompt 或 tool registry 中能看到插件能力摘要。
- 未授权 workspace / agent 看不到该能力。

### 场景 2：Skill context 注入

准备：

- 插件包含一个 `SKILL.md`。

验证：

- Agent 执行前能加载对应 Skill context。
- Skill context 不包含凭据。
- 关闭插件后 Skill context 不再注入。

### 场景 3：Tool invocation

准备：

- 插件暴露一个可调用工具。
- 配置必要 credential。

验证：

- 用户通过 `/api/agent/query` 提交自然语言请求。
- Agent 选择插件 tool。
- 调用进入 Plugin Invocation Gateway。
- 返回结构化结果。
- Agent 基于结果生成最终回答。

### 场景 4：权限和凭据失败

该场景不作为第一阶段阻塞项。第一阶段可以先验证接口占位和默认策略，后续治理阶段再补完整用例。

验证：

- 未配置凭据时，调用失败并返回可解释错误。
- 未授权 agent 调用时，Policy 拦截。
- 敏感操作没有确认时，策略拦截。
- 所有失败都有 audit。

### 场景 5：观测和审计

该场景不作为第一阶段阻塞项。第一阶段只要求保留 trace id / session id 传递位置，后续治理阶段再补完整审计和观测。

验证：

- Agent session id / trace id 能关联到 Plugin invocation。
- audit log 能回答“谁在什么 agent 下调用了什么插件能力”。
- runtime / invocation event 能回答“调用是否成功、耗时多少、错误是什么”。

## 集成测试通过标准

第一阶段通过标准：

- 至少一个测试插件能被当前 Agent 发现和调用。
- 至少一个 Skill context 能被当前 Agent 加载。
- 至少一个 OpenAPI / HTTP 插件能力能通过 Agent 自然语言请求触发。
- 如果纳入 MCP，则只验证 Streamable HTTP MCP。
- 不依赖 `plugin-poc` CLI 才能完成验收。
