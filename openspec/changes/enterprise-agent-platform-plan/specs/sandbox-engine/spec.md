## ADDED Requirements

### Requirement: Docker + K8s 双模式沙箱
系统 SHALL 支持 Docker 本地模式和 K8s Pod 模式两种沙箱后端，通过统一的 SandboxManager 接口切换。模式选择 SHALL 通过环境变量 SANDBOX_MODE 配置（docker / k8s / e2b）。

#### Scenario: Docker 模式启动沙箱
- **WHEN** SANDBOX_MODE=docker 且收到沙箱执行请求
- **THEN** 系统 SHALL 创建 Docker 容器，挂载临时工作目录，执行代码后销毁容器

#### Scenario: K8s 模式启动沙箱
- **WHEN** SANDBOX_MODE=k8s 且收到沙箱执行请求
- **THEN** 系统 SHALL 创建 K8s Pod，配置资源限制（CPU/Memory/Disk），执行完成后删除 Pod

#### Scenario: 模式切换
- **WHEN** 运行时切换 SANDBOX_MODE 配置
- **THEN** 新请求 SHALL 使用新模式，已运行的沙箱 SHALL 继续在原模式完成

### Requirement: 4 种网络策略
系统 SHALL 支持 4 种沙箱网络策略：NONE（完全隔离）、ALLOWLIST（白名单域名）、PROXY（通过代理访问）、FULL（完全开放）。策略 SHALL 根据任务风险等级自动选择。

#### Scenario: NONE 策略
- **WHEN** 任务风险等级为 HIGH 且不需要网络
- **THEN** 沙箱 SHALL 完全禁止网络访问，包括 DNS 解析

#### Scenario: ALLOWLIST 策略
- **WHEN** 任务需要访问特定 API
- **THEN** 沙箱 SHALL 仅允许访问白名单中的域名，其他请求被拒绝

#### Scenario: PROXY 策略
- **WHEN** 任务需要网络但需要审计
- **THEN** 所有网络请求 SHALL 通过代理服务器转发，代理 SHALL 记录请求日志并检测 SSRF

#### Scenario: FULL 策略
- **WHEN** 任务风险等级为 LOW 且需要完全网络访问
- **THEN** 沙箱 SHALL 允许所有网络访问，但 SHALL 记录所有出站连接

### Requirement: AST 代码验证
系统 SHALL 在沙箱执行前对代码进行 AST 静态分析，检测危险操作（如 os.system、subprocess、eval、exec、文件删除）。检测到危险操作 SHALL 根据策略拒绝或告警。

#### Scenario: 检测到危险调用
- **WHEN** 代码中包含 os.system("rm -rf /")
- **THEN** 系统 SHALL 拒绝执行并返回安全错误，记录审计日志

#### Scenario: 白名单内的系统调用
- **WHEN** 代码中包含 os.path.join()（白名单内）
- **THEN** 系统 SHALL 允许执行

#### Scenario: AST 解析失败
- **WHEN** 代码语法错误导致 AST 解析失败
- **THEN** 系统 SHALL 跳过 AST 检查，依赖沙箱隔离保障安全

### Requirement: Warm Pool 预热池
系统 SHALL 维护沙箱预热池，预先创建指定数量的空闲沙箱实例。请求到达时 SHALL 优先从预热池获取，减少冷启动延迟。

#### Scenario: 从预热池获取
- **WHEN** 预热池中有空闲沙箱
- **THEN** 系统 SHALL 在 500ms 内返回可用沙箱（vs 冷启动 5-10s）

#### Scenario: 预热池耗尽
- **WHEN** 预热池为空
- **THEN** 系统 SHALL 冷启动新沙箱，同时异步补充预热池

#### Scenario: 预热池自动扩缩
- **WHEN** 过去 5 分钟预热池命中率 < 50%
- **THEN** 系统 SHALL 增加预热池大小；命中率 > 90% 时缩减以节省资源

### Requirement: 沙箱自愈机制
系统 SHALL 监控沙箱健康状态，对 OOM、超时、僵死的沙箱自动回收重建。

#### Scenario: OOM 检测
- **WHEN** 沙箱内存使用超过限制触发 OOM
- **THEN** 系统 SHALL 终止沙箱，返回 OOM 错误，自动回收资源

#### Scenario: 执行超时
- **WHEN** 沙箱执行超过配置的超时时间（默认 300 秒）
- **THEN** 系统 SHALL 强制终止沙箱，返回超时错误

#### Scenario: 僵死检测
- **WHEN** 沙箱 30 秒内无任何输出且进程仍在运行
- **THEN** 系统 SHALL 发送健康检查，无响应则终止并重建

### Requirement: Pi Agent 实时日志
系统 SHALL 通过 JSONL IPC 协议实时获取沙箱内 Pi Agent 的执行日志，包括代码执行输出、错误信息、文件产物。

#### Scenario: 实时日志推送
- **WHEN** Pi Agent 在沙箱内执行代码并产生输出
- **THEN** 输出 SHALL 通过 JSONL 格式实时传输到宿主进程，延迟 < 200ms

#### Scenario: 产物提取
- **WHEN** Pi Agent 生成文件产物（图片/CSV/PDF）
- **THEN** 系统 SHALL 从沙箱中提取产物到宿主文件系统，并在响应中返回产物路径