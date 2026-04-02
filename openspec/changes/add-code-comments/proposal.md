## Why

项目整体开发已完成，进入代码 review 阶段。当前代码缺少必要的中文注释，模块职责、关键算法逻辑、设计决策等信息需要通过阅读大量上下文才能理解。添加结构化注释可以降低 review 成本，方便团队成员快速理解各模块的设计意图和实现细节。

## What Changes

- 为 `src/` 下所有 Python 模块添加模块级 docstring，说明模块职责和在整体架构中的位置
- 为核心类和公开方法添加中文 docstring，说明参数、返回值和关键行为
- 在复杂业务逻辑处（如 DAG 规划、中间件洋葱模型、沙箱 IPC 解析、Token 管理等）添加行内注释，解释"为什么这样做"
- 为 `frontend/src/` 下的核心 TypeScript 模块和组件添加 JSDoc 注释
- 为 `skill/` 目录下的脚本添加必要的功能说明注释

## Non-goals

- 不修改任何业务逻辑或代码行为
- 不重构代码结构或重命名变量
- 不为显而易见的简单代码添加冗余注释（如 getter/setter）
- 不添加 TODO/FIXME 等待办标记
- 不修改测试文件中的注释

## Capabilities

### New Capabilities
- `code-comments`: 覆盖后端 Python 模块、前端 TypeScript 组件、Skill 脚本的结构化注释添加

### Modified Capabilities

（无需修改现有 spec 的行为要求）

## Impact

- 影响范围：`src/`、`frontend/src/`、`skill/` 下的源代码文件
- 不影响 API 接口、依赖项或系统行为
- 仅增加注释内容，不改变代码逻辑