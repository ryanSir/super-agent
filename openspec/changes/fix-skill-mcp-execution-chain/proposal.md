## Why

Skill 执行链路存在多处 bug（包括一个导致 `NameError` 的硬性错误），MCP 客户端仅支持单端点配置，限制了多服务接入能力。这些问题直接影响 Skill 调用和 MCP 工具注入的可用性，需要在进一步功能开发前修复。

## What Changes

- **修复 `execute_skill` 中的 `NameError`**：`orchestrator_agent.py:458` 使用了未定义变量 `args`，应为 `params`，导致所有 Skill 沙箱调用必然崩溃
- **统一 `execute_skill` 工具签名**：`toolset_assembler.py` 中 direct agent 注册的 `execute_skill` 参数为 `args: List[str]`，与主 agent 的 `params: Dict[str, Any]` 不一致，direct 模式下调用 Skill 会出错
- **Skill 渐进式加载**：system prompt 中已注入 Skill 摘要（名称+描述），但缺少 `search_skills` 工具在 direct agent 中的注册，导致 direct 模式无法按需获取 Skill 完整定义
- **MCP 多端点支持**：`MCPSettings` 仅有单一 `mcp_server_url`，`create_mcp_servers_from_config()` 只能创建一个 server；需支持通过 `MCP_SERVERS` 配置多个命名端点（name + url + headers）
- **修复沙箱私有属性跨类访问**：`sandbox_worker.py:74` 直接访问 `self._manager._is_local`，应通过公共属性或方法暴露

## Capabilities

### New Capabilities

- `mcp-multi-endpoint`: 支持通过配置文件定义多个 MCP 端点，每个端点独立命名、独立 headers，统一注入 Orchestrator Agent

### Modified Capabilities

- `skills`: 修复 `execute_skill` 的 `NameError` bug，统一 direct/main agent 的工具签名，补全 direct agent 中 `search_skills` 工具注册
- `workers`: 修复 `SandboxWorker` 跨类访问私有属性的问题

## Impact

- `src/orchestrator/orchestrator_agent.py`：修复 `execute_skill` 中 `args` → `params`
- `src/orchestrator/toolset_assembler.py`：统一 `execute_skill` 签名，补注册 `search_skills`
- `src/config/settings.py`：`MCPSettings` 新增 `mcp_servers` 列表字段
- `src/mcp/client.py`：`create_mcp_servers_from_config()` 支持多端点遍历
- `src/workers/sandbox/sandbox_worker.py`：改用 `SandboxManager` 公共接口判断模式

## Non-goals

- 不重构 Skill 执行模式（沙箱 vs 本地直接执行的策略选择不在本次范围内）
- 不修改 MCP 工具过滤逻辑（`_BLOCKED_TOOLS` 维护不变）
- 不引入 MCP 动态发现或热重载机制
