"""安全系统 — 工具级权限模型

通过 pydantic_ai_shields.ToolGuard capability 实现配置化的工具访问控制。

配置方式：
- BLOCKED_TOOLS 环境变量：逗号分隔的工具黑名单，被拦截的工具调用会触发 ModelRetry
- 示例：BLOCKED_TOOLS=dangerous_tool,risky_tool

注册路径：
- config/settings.py → HooksSettings.blocked_tools
- orchestrator/agent_factory.py → ToolGuard(blocked=[...]) 注册到 create_deep_agent(capabilities=[...])

扩展方向：
- require_approval: 需要人工审批的工具列表（对接 WebSocket 双向通信）
- approval_callback: 自定义审批回调函数
"""
