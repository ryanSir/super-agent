## 1. 数据模型变更

- [x] 1.1 在 `src/config/settings.py` 的 `MCPSettings` 中新增 `mcp_servers: str` 字段（JSON 字符串，alias `MCP_SERVERS`，默认空字符串）

## 2. Bug 修复：execute_skill NameError

- [x] 2.1 在 `src/orchestrator/orchestrator_agent.py` 的 `execute_skill` 工具中，将 `SandboxTask(task_id=f"skill-{skill_name}-{id(args) % 10000}", ...)` 中的 `args` 改为 `params`

## 3. SandboxManager 封装修复

- [x] 3.1 在 `src/workers/sandbox/sandbox_manager.py` 中将 `_is_local` property 重命名为 `is_local`（去掉下划线前缀，保持 `@property` 装饰器）
- [x] 3.2 在 `src/workers/sandbox/sandbox_worker.py` 中将 `self._manager._is_local` 改为 `self._manager.is_local`

## 4. MCP 多端点支持

- [x] 4.1 在 `src/mcp/client.py` 中新增 `_parse_mcp_servers_config()` 函数，解析 `settings.mcp.mcp_servers` JSON 字符串，返回 `List[Dict]`，解析失败时记录 warning 并返回空列表
- [x] 4.2 修改 `src/mcp/client.py` 的 `create_mcp_servers_from_config()`：优先遍历 `_parse_mcp_servers_config()` 结果创建多端点，若结果为空则回退到 `mcp_server_url` 单端点逻辑

## 5. Skill 执行链路修复：统一签名 + 补全 direct agent

- [x] 5.1 在 `src/orchestrator/toolset_assembler.py` 的 `_register_direct_tools()` 中，将 `execute_skill` 工具的参数从 `args: List[str]` 改为 `params: Dict[str, TypAny]`，并更新转发调用
- [x] 5.2 在 `src/orchestrator/toolset_assembler.py` 的 `_register_direct_tools()` 中，补充注册 `search_skills` 工具（转发到 `orchestrator_agent.search_skills`）
