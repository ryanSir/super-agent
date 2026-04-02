## ADDED Requirements

### Requirement: 模块级 docstring
每个 Python 源文件（`src/**/*.py`）SHALL 在文件顶部包含模块级 docstring，说明该模块的职责、在整体架构中的位置以及关键依赖关系。

#### Scenario: 标准 Python 模块
- **WHEN** 打开 `src/` 下任意 `.py` 文件
- **THEN** 文件顶部（import 语句之前）存在三引号 docstring，包含模块职责描述

#### Scenario: __init__.py 文件
- **WHEN** 打开 `src/` 下任意 `__init__.py` 文件
- **THEN** 若该文件包含实质性代码或导出逻辑，SHALL 包含 docstring 说明包的用途；若为空文件则无需添加

### Requirement: 核心类 docstring
核心类（承担关键业务逻辑的类）SHALL 包含类级 docstring，说明类的职责、关键属性和使用方式。

#### Scenario: Worker 类
- **WHEN** 查看 `src/workers/` 下的 Worker 类定义
- **THEN** 类定义下方存在 docstring，说明该 Worker 的职责、风险等级（SAFE/DANGEROUS）、输入输出格式

#### Scenario: Orchestrator Agent 类
- **WHEN** 查看 `src/orchestrator/orchestrator_agent.py` 中的核心类
- **THEN** 类 docstring 说明编排逻辑、工具注册方式、中间件集成方式

### Requirement: 公开方法 docstring
核心类的公开方法（非下划线开头）SHALL 包含 Google Style docstring，说明 Args、Returns、Raises。

#### Scenario: 带参数的公开方法
- **WHEN** 查看核心类中接受参数的公开方法
- **THEN** docstring 包含 Args 段落，列出每个参数的名称和用途说明

#### Scenario: 有返回值的公开方法
- **WHEN** 查看核心类中有返回值的公开方法
- **THEN** docstring 包含 Returns 段落，说明返回值类型和含义

#### Scenario: 可能抛出异常的方法
- **WHEN** 查看显式 raise 异常的公开方法
- **THEN** docstring 包含 Raises 段落，说明异常类型和触发条件

### Requirement: 复杂逻辑行内注释
复杂业务逻辑段落 SHALL 包含行内注释，解释设计决策和"为什么这样做"。

#### Scenario: DAG 规划逻辑
- **WHEN** 查看 `src/orchestrator/planner.py` 中的 DAG 生成逻辑
- **THEN** 关键步骤处存在注释，解释拓扑排序、并行度控制等设计决策

#### Scenario: 中间件管道执行
- **WHEN** 查看 `src/middleware/pipeline.py` 中的洋葱模型执行逻辑
- **THEN** 注释说明 before/after 钩子的执行顺序和错误传播策略

#### Scenario: 沙箱 IPC 解析
- **WHEN** 查看 `src/workers/sandbox/ipc.py` 中的 JSONL 解析逻辑
- **THEN** 注释说明消息格式约定、事件类型映射规则

#### Scenario: Token 管理
- **WHEN** 查看 `src/llm/token_manager.py` 中的临时 JWT 签发逻辑
- **THEN** 注释说明 TTL 设置原因、scope 限制策略

### Requirement: 前端 JSDoc 注释
`frontend/src/` 下的核心 TypeScript 模块和 React 组件 SHALL 包含 JSDoc 注释，说明组件/模块的职责和关键 props。

#### Scenario: 引擎模块
- **WHEN** 查看 `frontend/src/engine/` 下的 `.ts` 文件
- **THEN** 文件顶部或主要导出函数/类上方存在 JSDoc 注释，说明模块职责

#### Scenario: React 组件
- **WHEN** 查看 `frontend/src/components/` 下的 `.tsx` 文件
- **THEN** 组件函数上方存在 JSDoc 注释，说明组件用途和关键 props

### Requirement: Skill 脚本注释
`skill/` 目录下的可执行脚本 SHALL 在文件顶部包含功能说明注释，描述脚本用途、输入参数和输出格式。

#### Scenario: Python 技能脚本
- **WHEN** 查看 `skill/*/scripts/*.py` 文件
- **THEN** 文件顶部存在 docstring 或注释块，说明脚本功能、命令行参数、输出格式

### Requirement: 注释语言规范
所有注释 SHALL 使用中文编写，代码标识符保持英文不变。

#### Scenario: Python docstring
- **WHEN** 查看任意新增的 Python docstring
- **THEN** 描述文本为中文，参数名和类型标注保持英文

#### Scenario: TypeScript JSDoc
- **WHEN** 查看任意新增的 JSDoc 注释
- **THEN** 描述文本为中文，类型和参数名保持英文

### Requirement: 不添加冗余注释
显而易见的简单代码 SHALL NOT 添加注释，包括简单赋值、getter/setter、直接的字段映射等。

#### Scenario: 简单赋值语句
- **WHEN** 代码为 `self.name = name` 等简单赋值
- **THEN** 不添加行内注释

#### Scenario: 直接委托调用
- **WHEN** 方法体仅为单行 return 或直接调用另一个方法
- **THEN** 不添加行内注释，仅在方法签名处添加 docstring（如有必要）
