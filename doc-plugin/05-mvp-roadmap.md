# 05. MVP 范围和路线图

## 目标

本文件定义 Plugin 系统第一版应该做什么、不做什么，以及后续路线图。

这里的 MVP 指 **Minimum Viable Product，最小可行产品**。在本文档中，也可以直接理解为“第一版”。

## 第一版范围

第一版建议聚焦：

1. Plugin manifest schema
2. Plugin registry 基础能力
3. Plugin install/enable/disable
4. OpenAPI connector plugin
5. Streamable HTTP MCP plugin
6. mcpo-like adapter 方案验证
7. Skill plugin
8. Credential schema + encrypted storage
9. Policy check + audit log
10. Tool invocation gateway
11. Local dev CLI
12. 2-3 个官方示例插件

## 第一版官方示例

建议准备 2-3 个官方示例插件，用来验证插件模型和开发体验。

候选示例：

- 企业知识库 Data Source Plugin
- Jira/飞书/Slack API Connector Plugin
- MCP filesystem 或 GitHub MCP Plugin
- 周报生成 Skill Plugin

示例插件的目标不是覆盖所有场景，而是验证：

- manifest 是否能表达能力。
- credential 是否能完成配置和测试。
- Agent 是否能发现并调用插件能力。
- 权限和审计是否能覆盖关键调用。
- 插件开发者是否能按 SDK/CLI 完成本地开发和发布。

## 第一版不建议纳入

第一版暂不建议做：

- 外部开放 marketplace。
- 插件商业化结算。
- App/UI Plugin 完整沙箱。
- Trigger Plugin 完整事件系统。
- Workflow Plugin 完整编排系统。
- Agent Strategy Plugin 暂不纳入正式能力模型。
- Model Provider Plugin。
- 完整 serverless runtime。
- 复杂多版本灰度发布系统。

原因是这些能力会显著扩大安全、运行时和产品复杂度，不利于第一版快速闭环。

## 二期路线图

二期可以做：

- Plugin marketplace
- 插件签名和安全扫描
- App/UI Plugin
- Workflow Plugin
- Trigger Plugin
- Serverless runtime
- 插件调用成本统计
- 插件权限审批流
- 多版本灰度和回滚
- 插件评分、文档、示例库

三期再考虑：

- Model Provider Plugin
- 插件组合编排
- 插件商业化结算
- 外部开发者生态

Agent Strategy Plugin 这类能力会影响 Agent Runtime 的核心规划和执行机制，当前阶段先不纳入路线图，相关任务级行为指导优先通过 Skill Plugin 承载。

## 本周建议产出

本周建议完成 6 个成果：

1. Plugin 概念定义文档
2. Plugin 能力模型与 manifest 草案
3. Plugin Runtime 架构图
4. MCP/OpenAPI 接入策略
5. MVP 范围和路线图
6. 开源参考与复用策略

## 暂不做估时

当前阶段先不加入人力和周期估算。原因是估时依赖以下关键细节：

- 第一版最终支持哪些 plugin 类型。
- Runtime 是 daemon、sidecar、container 还是 remote。
- MCP stdio 是否要平台托管。
- Credential 和 Policy 做到什么深度。
- 是否要做 UI Plugin / marketplace。
- 是否复用开源代码，复用到什么程度。
- 现有平台已有多少基础能力可用。

等范围、架构、安全边界和开源复用方式确认后，再补充 `07-effort-estimation-and-team-plan.md`。
