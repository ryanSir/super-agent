# Super-Agent 产线安全性分析

> 基于当前代码库（branch: agent-core-v2）实际扫描，2026-04-22

---

## 一、已实现的安全机制

### 1. 工具黑名单（ToolGuard）
- **位置**：`orchestrator/agent_factory.py:62-70`
- **实现**：通过 `pydantic_ai_shields.ToolGuard` 注册到 Agent capabilities
- **配置**：`BLOCKED_TOOLS` 环境变量，逗号分隔工具名
- **行为**：被拦截的工具调用触发 `ModelRetry`，Agent 会重新规划
- **依赖风险**：`pydantic_ai_shields` 未安装时静默跳过，仅打 warning 日志

### 2. 循环检测（Loop Guard）
- **位置**：`config/settings.py` → `HooksSettings`
- **参数**：
  - `LOOP_WINDOW_SIZE=20`：检测窗口
  - `LOOP_WARN_THRESHOLD=3`：触发警告阈值
  - `LOOP_HARD_LIMIT=5`：强制中断阈值
- **实现**：由 `orchestrator/hooks.py` 中的 `create_hooks()` 注入 pydantic-deep 框架

### 3. LLM 请求次数限制
- **位置**：`gateway/rest_api.py:_run_agent()`
- **实现**：`UsageLimits(request_limit=15)`，单次 Agent 运行最多向 LLM 发起 15 次请求
- **作用**：防止失控的 Agent 无限消耗 token

### 4. 并发 Sub-Agent 限制
- **位置**：`config/settings.py` → `AppSettings.max_concurrent_subagents=3`
- **作用**：限制同时运行的 Sub-Agent 数量，防止资源耗尽

### 5. 沙箱隔离
- **开发模式**（`E2B_USE_LOCAL=true`）：本地进程隔离
- **生产模式**：E2B Cloud 云端沙箱，代码在隔离容器中执行
- **临时 Token**：E2B 模式下通过 `issue_sandbox_token()` 签发临时 LLM token，不暴露主 API Key

### 6. 记忆系统超时降级
- **位置**：`config/settings.py` → `MemorySettings.retrieval_timeout_ms=200`
- **作用**：Redis 记忆检索超时后降级继续执行，防止记忆系统故障阻塞主流程

### 7. 可观测性
- Langfuse 追踪（`monitoring/langfuse_tracer.py`）：记录 agent_query span，含 input/output/error
- 结构化日志：session_id + trace_id 全链路透传

---

## 二、已声明但未实现的安全模块（TODO）

| 模��� | 文件 | 状态 | 说明 |
|------|------|------|------|
| Prompt 注入检测 | `security/injection_guard.py` | **TODO** | 检测 tool result 和用户输入中的越权指令 |
| 沙箱安全策略 | `security/sandbox_policy.py` | **TODO** | 网络白名单、文件系统限制、资源限额 |
| 审计日志 | `security/audit.py` | **TODO** | 工具调用链追踪，按 session/user/time 查询 |
| 权限模型 | `security/permissions.py` | **仅文档** | 工具级权限模型，require_approval 等未实现 |

---

## 三、当前安全风险

### 高危

#### 3.1 所有 API 接口无认证
- **位置**：`main.py:create_app()`、`gateway/rest_api.py`
- **现象**：FastAPI 应用未注册任何认证中间件，`jwt_secret` 配置项存在但从未使用
- **影响**：任何人可提交查询、订阅任意 session 的 SSE 流、调用管理接口
- **受影响接口**：
  - `POST /api/agent/query` — 提交任意查询
  - `GET /api/agent/stream/{session_id}` — 订阅任意会话事件流
  - `POST /api/agent/admin/reload-mcp` — 触发 MCP 重载
  - `POST /api/agent/admin/reload-models` — 触发模型目录重载
  - `PATCH /api/agent/roles/{role}` — 修改角色模型绑定（内存生效）
  - `POST /api/agent/skills` — 创建任意 Skill 脚本

#### 3.2 Skill 创建接口可写入任意脚本
- **位置**：`gateway/rest_api.py:create_skill_endpoint()`
- **现象**：`POST /api/agent/skills` 接受 `script_content` 字段，写入 `skill/` 目录后 Agent 可执行
- **影响**：无认证情况下，攻击者可上传恶意 Skill 脚本并触发执行

#### 3.3 CORS 全开
- **位置**：`main.py:create_app()` → `allow_origins=["*"]`
- **影响**：任意域名的前端页面可跨域调用 API，结合无认证问题风险倍增

### 中危

#### 3.4 本地沙箱模式直接传递真实 API Key
- **位置**：`workers/sandbox/sandbox_worker.py:_do_execute()`
- **现象**：`E2B_USE_LOCAL=true` 时 `llm_token = settings.llm.api_key`，真实 key 写入沙箱启动脚本
- **影响**：沙箱内进程可读取并泄露主账号 API Key

#### 3.5 JWT Secret 弱默认值
- **位置**：`config/settings.py` → `jwt_secret: str = Field(default="super-agent-secret")`
- **影响**：若未来启用 JWT 认证但未修改默认值，攻击者可伪造 token

#### 3.6 Redis 无认证/加密
- **位置**：`config/settings.py` → `RedisSettings.password=''`
- **影响**：Redis 默认无密码，会话数据、对话历史、事件流均明文存储；内网横向移动可读取所有数据

#### 3.7 Prompt 注入检测缺失
- **位置**：`security/injection_guard.py`（仅 TODO）
- **影响**：工具返回内容（如网页抓取、数据库查询结果）中的恶意指令可直接影响 Agent 行为

### 低危

#### 3.8 管理接口无速率限制
- `POST /api/agent/admin/reload-mcp` 和 `reload-models` 无频率限制，可被用于 DoS

#### 3.9 SSE session_id 可枚举
- `GET /api/agent/stream/{session_id}` 中 session_id 格式为 `s-{12位hex}`，理论上可暴力枚举

#### 3.10 ToolGuard 依赖静默失效
- `pydantic_ai_shields` 未安装时工具黑名单静默跳过，无告警机制

---

## 四、修复优先级建议

| 优先级 | 问题 | 建议方案 |
|--------|------|----------|
| P0 | API 无认证 | 添加 API Key 或 JWT Bearer 中间件，至少保护 admin 和 skills 接口 |
| P0 | Skill 创建无权限 | 生产环境禁用或加白名单鉴权 |
| P1 | CORS 全开 | 生产环境配置具体域名白名单 |
| P1 | 本地模式 API Key 泄露 | 本地模式也应签发临时 token 或限制 key 权限 |
| P1 | Redis 无认证 | 配置 Redis 密码 + TLS，或限制网络访问 |
| P2 | JWT Secret 默认值 | 强制要求生产环境设置 `JWT_SECRET` 环境变量，启动时校验 |
| P2 | Prompt 注入检测 | 实现 `injection_guard.py`，至少对 tool result 做关键词过滤 |
| P3 | 审计日志 | 实现 `audit.py`，记录工具调用链，支持事后溯源 |
| P3 | 管理接口速率限制 | 添加 slowapi 或 nginx 层限流 |

---

## 五、架构层面安全建议

1. **分层防御**：在 nginx/API Gateway 层做认证，不依赖应用层
2. **最小权限原则**：沙箱 Pi Agent 只应获得完成当前任务所需的最小 token 权限
3. **Skill 沙箱化**：Skill 脚本执行应在沙箱内，而非主进程
4. **Secret 管理**：API Key、Redis 密码等敏感配置应通过 Vault 或 K8s Secret 注入，不走 `.env` 文件
5. **审计完整性**：审计日志应写入独立存储（非同一 Redis），防止被篡改