计划：Claude Code + OpenSpec 环境搭建与实践

 Context

 文章核心观点：AI 编码的瓶颈不是模型能力，而是上下文管理失效和开发意图模糊。
 解法是 Claude Code（代理化执行）+ OpenSpec（规格化驱动）双轮驱动，构建闭环 AI 研发体系。

 当前项目 super-agent-poc 已实现了完整的 agent 架构（Orchestrator + Workers + Skills + Temporal 工作流），
 后续新功能将基于 SDD（规格驱动开发）范式开发，验证这套范式对后端 AI 工程师的实际价值。

 ---
 第一部分：文章核心概念速览

 为什么需要这套范式？

 - AI 在短上下文（1K token）准确率 99.3%，扩展到 32K token 暴跌至 69.7%
 - 传统 AI 辅助：意图靠猜 → 上下文污染 → 修正循环 → 人工干预增加
 - SDD 解法：先锁定规格，再让 AI 按规格执行，消除意图模糊

 核心工作流（三阶段）

 Propose（提案）→ Apply（执行）→ Archive（归档）
 - Propose：人 + AI 协商，生成 proposal.md / specs/ / design.md / tasks.md
 - Apply：AI 严格按 tasks.md 逐项实施，自动运行测试
 - Archive：完成后归档变更，核心规格更新至 openspec/specs/，保持上下文"卫生"

 ---
 第二部分：OpenSpec 环境搭建步骤（手动执行）

 前置条件检查

 node --version   # 需要 >= 20.19.0
 npm --version

 Step 1：全局安装 OpenSpec CLI

 npm install -g @fission-ai/openspec@latest

 Step 2：在项目根目录初始化

 cd /Users/zhangyang/Desktop/code/super-agent-poc
 openspec init
 初始化后会生成：
 openspec/
 ├── specs/          # 当前项目规格（持久化，描述系统现状）
 └── changes/        # 变更提案（临时，完成后归档）

 Step 3：确认 Claude Code 已安装

 claude --version   # 确认 CC 可用

 Step 4：在项目根目录创建/更新 CLAUDE.md

 OpenSpec 初始化后会自动注入 /opsx:* 命令到 Claude Code，
 但建议手动在 CLAUDE.md 中补充项目约束（见第三部分）。

 ---
 第三部分：在 super-agent-poc 中的实践方案

 3.1 为现有核心模块补充规格（一次性工作）

 在 openspec/specs/ 下为已有模块创建规格文档，让 AI 后续修改时有上下文：

 ┌──────────────────┬───────────────────────────────────────────────┐
 │     规格文件     │                   对应模块                    │
 ├──────────────────┼───────────────────────────────────────────────┤
 │ orchestrator.md  │ src/orchestrator/ - DAG 规划、任务路由逻辑    │
 ├──────────────────┼───────────────────────────────────────────────┤
 │ workers.md       │ src/workers/ - Native/Sandbox Worker 边界规则 │
 ├──────────────────┼───────────────────────────────────────────────┤
 │ skills.md        │ src/skills/ - 技能注册、执行约束              │
 ├──────────────────┼───────────────────────────────────────────────┤
 │ streaming.md     │ src/streaming/ - SSE/WebSocket 事件协议       │
 ├──────────────────┼───────────────────────────────────────────────┤
 │ a2ui-protocol.md │ src/schemas/a2ui.py - 前端渲染协议            │
 └──────────────────┴───────────────────────────────────────────────┘

 3.2 新功能开发标准流程

 以后每个新功能按以下流程走：

 Step 1 - 提案
 /opsx:propose "功能描述，例如：为 Orchestrator 增加任务重试机制，支持指数退避"
 CC 会分析现有代码，在 openspec/changes/<feature-name>/ 下生成：
 - proposal.md - 变更动机和范围
 - specs/ - 具体场景描述（输入/输出）
 - design.md - 技术方案（涉及哪些文件、接口变更）
 - tasks.md - 原子化任务清单

 Step 2 - 人工审阅规格
 重点检查：
 - 是否覆盖了边界场景（并发、失败、超时）
 - 是否与现有架构约束冲突（如 Temporal 工作流的幂等性要求）
 - 直接修改 specs/ 文件补充遗漏场景

 Step 3 - 执行
 /opsx:apply
 CC 按 tasks.md 逐项实施，自动运行测试，失败自动修复。

 Step 4 - 归档
 /opsx:archive
 变更文档归档，核心规格更新至 openspec/specs/。

 3.3 推荐的第一个实践任务

 建议用一个中等复杂度的新功能来验证这套范式，例如：
 - 为 Skills 系统增加版本管理（涉及 registry.py + schema.py + executor.py）
 - 为 Orchestrator 增加任务超时与重试（涉及 workflows.py + activities.py）

 这类任务跨 2-3 个文件，有明确的边界场景，适合验证 SDD 的价值。

 ---
 验证方式

 1. openspec init 后检查目录结构是否正确生成
 2. 在 Claude Code 中执行 /opsx:propose 确认命令可用
 3. 完成一个完整的 Propose → Apply → Archive 循环
 4. 对比：同样复杂度的功能，SDD 流程 vs 直接让 AI 写代码，哪个结果更可控

 ---
 参考链接

 - OpenSpec GitHub: https://github.com/Fission-AI/OpenSpec
 - Spec Kit (GitHub 官方): https://github.com/github/spec-kit
 - 文章原文: https://mp.weixin.qq.com/s/aHAJxvrwobUKsPZ3w7GnYw
