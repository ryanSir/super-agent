## Context

当前系统存在三类问题：

1. **硬性 Bug**：`orchestrator_agent.py` 的 `execute_skill` 工具在构建 `SandboxTask` 时引用了未定义变量 `args`（应为 `params`），导致所有 Skill 沙箱调用必然抛出 `NameError`，完全不可用。

2. **签名不一致**：`toolset_assembler.py` 中 direct agent 注册的 `execute_skill` 参数为 `args: List[str]`，与主 agent 的 `params: Dict[str, Any]` 不一致；同时 direct agent 缺少 `search_skills` 工具，导致 direct 模式下渐进式 Skill 加载链路断裂。

3. **MCP 单端点限制**：`MCPSettings` 只有一个 `mcp_server_url`，无法接入多个 MCP 服务（如同时接入内部工具服务和第三方服务）。

4. **私有属性跨类访问**：`SandboxWorker` 直接读取 `self._manager._is_local`，破坏封装边界。

## Goals / Non-Goals

**Goals:**
- 修复 `execute_skill` 的 `NameError`，使 Skill 沙箱执行链路可用
- 统一 main agent 和 direct agent 的 `execute_skill` 工具签名
- 补全 direct agent 的 `search_skills` 注册，保证渐进式加载完整
- 支持通过 `MCP_SERVERS` 环境变量配置多个 MCP 端点
- 消除 `SandboxWorker` 对 `SandboxManager` 私有属性的直接访问

**Non-Goals:**
- 不改变 Skill 执行策略（沙箱 vs 本地直接执行）
- 不引入 MCP 动态发现或热重载
- 不修改 `_BLOCKED_TOOLS` 过滤逻辑

## Decisions

### 1. `execute_skill` 统一使用 `params: Dict[str, Any]`

`List[str]` 是早期设计遗留，无法表达结构化参数（如 `{"query": "xxx", "limit": 10}`）。统一为 `Dict[str, Any]` 后，direct agent 和 main agent 行为一致，且与沙箱 instruction 构建逻辑对齐。

### 2. MCP 多端点：JSON 数组环境变量

**方案 A**：多个 `MCP_SERVER_URL_1`, `MCP_SERVER_URL_2` 环境变量
**方案 B**：单个 `MCP_SERVERS` 环境变量，值为 JSON 数组 `[{"name":"x","url":"...","headers":{}}]`

选择方案 B。理由：数量不固定时方案 A 需要遍历枚举，配置繁琐；方案 B 一个变量表达完整拓扑，与 Docker/K8s 配置实践一致。向后兼容：若 `MCP_SERVERS` 未配置则回退到 `MCP_SERVER_URL` 单端点行为。

### 3. `SandboxManager` 暴露 `is_local` 公共属性

将 `_is_local` property 改为公共 `is_local`（去掉下划线前缀），`SandboxWorker` 改用 `self._manager.is_local`。这是最小改动，不引入新接口。

## Risks / Trade-offs

- **`MCP_SERVERS` JSON 解析失败** → 记录 warning 并回退到 `MCP_SERVER_URL`，不阻断启动
- **direct agent 工具签名变更** → direct agent 是 lazy 初始化单例，重启后生效，无热更新问题
- **多 MCP 端点中某个不可达** → 单个 server 创建失败时跳过并记录 error，不影响其他 server

## Migration Plan

1. 修改代码（无数据迁移）
2. 若使用多端点，在 `.env` 中新增 `MCP_SERVERS` 配置；原 `MCP_SERVER_URL` 继续有效
3. 重启服务即可生效，无需数据库变更或前端发布
