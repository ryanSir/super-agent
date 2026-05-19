# 06. Claude Code 深度分析

## 结论先行

Claude Code 适合作为 Agent 客户端扩展体系的产品形态参考。它展示了 skills、MCP、slash commands、hooks、subagents、LSP、monitors、settings 和 plugin marketplace 如何组合，但它偏本地 CLI 和项目目录模型，不能直接照搬到企业服务端平台。

## 适用模块

- Skill Plugin。
- MCP Plugin。
- Plugin marketplace。
- 配置作用域。
- hooks / monitors / subagents 的后续扩展参考。

## 需要重点分析的问题

- skills 如何被发现、加载和注入上下文。
- MCP server 配置和权限体验。
- slash commands 与 workflow entry 的关系。
- hooks 和 monitors 的安全边界。
- subagents 如何定义工具权限和独立上下文。
- settings 如何区分用户级、项目级和组织级。
- plugin marketplace 如何安装、启用和升级。

## 可复用点

- Agent 扩展产品形态。
- Skill 作为上下文能力的设计。
- settings / permissions 分层思路。
- hooks、monitors、subagents 的长期能力参考。

## 不适合直接复用的点

- 本地 CLI 执行模型不能直接等价于企业服务端多租户平台。
- hooks、monitors、subagents 都可能影响 Agent Runtime 核心边界，不适合第一阶段直接开放。
- 凭据、权限、审计和观测需要服务化重建。

## 建议动作

- 作为 P1 产品形态分析。
- 与现有 [Claude Code 插件机制分析](../../design/08-claude-code-plugin-analysis.md) 对齐。
- 输出哪些能力进入 Plugin 范围、哪些应归为 Agent Runtime / Agent Template 的判断。

