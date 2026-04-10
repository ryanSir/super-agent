## ADDED Requirements

### Requirement: 五大文件操作
系统 SHALL 提供 Read / Write / Edit / Glob / Grep 五大文件操作，作为 Agent 的内置工具。所有操作 SHALL 在用户 workspace 范围内执行，禁止访问 workspace 外的文件。

#### Scenario: Read 文件
- **WHEN** Agent 调用 read_file("/workspace/data.csv")
- **THEN** 系统 SHALL 返回文件内容，大文件（> 1MB）SHALL 返回前 N 行并提示截断

#### Scenario: Write 文件
- **WHEN** Agent 调用 write_file("/workspace/output.txt", content)
- **THEN** 系统 SHALL 写入文件，如果文件已存在 SHALL 覆盖，记录审计日志

#### Scenario: Edit 文件
- **WHEN** Agent 调用 edit_file("/workspace/code.py", old_str, new_str)
- **THEN** 系统 SHALL 精确替换 old_str 为 new_str，old_str 不存在时返回错误

#### Scenario: Glob 搜索
- **WHEN** Agent 调用 glob_search("**/*.py")
- **THEN** 系统 SHALL 返回 workspace 内所有匹配的 Python 文件路径列表

#### Scenario: Grep 搜索
- **WHEN** Agent 调用 grep_search("def main", "*.py")
- **THEN** 系统 SHALL 返回包含 "def main" 的文件路径和行号

#### Scenario: 路径越权
- **WHEN** Agent 尝试访问 "/etc/passwd" 或 "../../../secret"
- **THEN** 系统 SHALL 拒绝操作并返回权限错误

### Requirement: Permission ACL
系统 SHALL 实现 per-user 文件权限控制，支持 read / write / execute 三种权限。权限规则 SHALL 支持路径通配符。

#### Scenario: 权限检查
- **WHEN** 用户 A 尝试写入只读目录
- **THEN** 系统 SHALL 拒绝操作并返回 "Permission denied"

#### Scenario: 通配符规则
- **WHEN** ACL 规则为 "/workspace/data/**" → read_only
- **THEN** 该目录下所有文件 SHALL 只允许读取，禁止写入和删除

### Requirement: 虚拟路径映射
系统 SHALL 支持虚拟路径到物理路径的映射，用户看到的路径（/workspace/...）SHALL 映射到实际存储路径。不同用户的 workspace SHALL 物理隔离。

#### Scenario: 路径映射
- **WHEN** 用户 A 访问 /workspace/data.csv
- **THEN** 系统 SHALL 映射到 /data/users/A/workspace/data.csv

#### Scenario: 跨用户隔离
- **WHEN** 用户 A 尝试通过路径遍历访问用户 B 的文件
- **THEN** 系统 SHALL 拒绝访问，路径解析 SHALL 限制在用户自己的物理目录内

### Requirement: File Watching 变更监听
系统 SHALL 支持文件变更监听，当 workspace 内文件被修改时 SHALL 推送变更事件到前端。

#### Scenario: 文件修改通知
- **WHEN** Agent 修改了 /workspace/code.py
- **THEN** 系统 SHALL 推送 file_changed 事件，包含文件路径和变更类型（created/modified/deleted）

#### Scenario: 批量变更合并
- **WHEN** 短时间内（< 500ms）发生多次文件变更
- **THEN** 系统 SHALL 合并为一次通知，避免事件风暴
