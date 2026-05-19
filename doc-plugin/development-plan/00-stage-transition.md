# 00. 从 POC 到生产开发的阶段转换

## 当前阶段判断

Plugin 总体报告、能力规划、端到端链路、POC 验收和开源参考文档已经基本完成。当前阶段可以结束“概念验证”，进入“详细设计和模块开发”。

但这里需要明确：`plugin-poc/` 的定位是验证可行性，不是生产功能雏形。它证明了以下事情：

- Plugin 可以被声明、校验、打包、发布、安装和启用。
- 能力可以进入 Capability Index，并绑定到 workspace / agent。
- Agent 调用可以统一经过 Policy、Credential、Gateway 和 Runtime。
- OpenAPI、MCP、Skill、Data Source 等能力类型可以共享主链路。
- Audit / Events 可以成为调用链路的一部分。

它没有解决生产化问题：

- 没有正式数据库和状态模型。
- 没有 HTTP API / SDK。
- 没有接入当前 `src_deepagent` 的能力注册和 Agent Runtime。
- 没有接入公司 IAM、密钥系统、观测平台和后台。
- 没有真实 OpenAPI 调用、MCP stdio 托管、权限治理和管理后台。

## 下一阶段目标

下一阶段目标不是“继续补 POC”，而是把 POC 验证出的模块边界转成生产设计和代码实现。

建议目标：

1. 定义生产模块边界和数据模型。
2. 明确哪些模块进入第一阶段开发，哪些暂缓。
3. 明确哪些模块自研、哪些接公司系统、哪些参考或局部复用开源。
4. 建立当前 Agent 项目的集成测试路径。
5. 先完成一个最小生产闭环，再逐步扩展能力类型和治理能力。

## 推荐工作流

```text
总体报告确认
  -> 模块详细设计
  -> 开源深度分析
  -> 数据模型 / API 设计
  -> 最小生产闭环开发
  -> 当前 Agent 集成测试
  -> 管理后台 / 观测 / 安全增强
```

## 第一阶段建议范围

第一阶段建议先做 Plugin 主体功能闭环，目标是让当前 Agent 能真实发现和调用插件能力。权限校验、凭据治理、审计和完整安全策略先预留接口，不作为第一阶段阻塞项。

- Plugin manifest 和 package layout。
- Registry / package 存储抽象。
- Plugin Manager：安装、启用、禁用、版本状态。
- Capability Index：workspace / agent 级能力索引。
- Plugin Core API：能力发现、Skill context、Tool invocation。
- OpenAPI / HTTP connector 的真实调用。
- Streamable HTTP MCP 的基础调用。
- 当前 `src_deepagent` 的集成测试。

第一阶段不建议强制包含：

- 完整 Credential / Policy / Audit 治理闭环。
- 完整 Runtime Host。
- 完整 container / serverless runtime。
- stdio MCP adapter。
- App/UI Plugin。
- Workflow / Trigger Plugin。
- Agent Strategy Plugin。
- 复杂 marketplace 审核流。

这些可以保留设计空间，但不作为第一阶段阻塞项。
