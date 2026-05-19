# Plugin 生产化开发规划

本目录用于承接 `doc-plugin/` 下已有的规划报告和 POC 验证文档，把“Plugin 能力可行性”推进到“生产功能开发”阶段。

当前判断：

- `plugin-poc/` 已经验证 Plugin 主链路可行，但它不是完整可用的生产功能。
- 当前仓库本身已经有一个 Agent 项目，即 `src_deepagent/`，后续 Plugin 功能开发完成后，应优先用当前 Agent 做集成测试。
- 下一阶段不应直接在 POC 上堆功能，而应先完成详细设计，再按模块进入开发。
- 对可能复用或参考的开源项目，需要做模块级深度分析，而不是笼统判断“用某个框架”。

建议阅读顺序：

1. [00-阶段转换说明](./00-stage-transition.md)
2. [01-模块开发总计划](./01-module-development-plan.md)
3. [02-当前 Agent 集成测试计划](./02-current-agent-integration-test-plan.md)
4. [03-开源深度分析计划](./03-open-source-deep-dive-plan.md)
5. [模块详细设计目录](./modules/)
6. [开源深度分析目录](./open-source-deep-dive/)

与已有文档的关系：

| 目录 / 文档 | 定位 |
| --- | --- |
| `doc-plugin/01-plugin-platform-technical-director-report.md` | 面向技术负责人汇报的总体报告 |
| `doc-plugin/design/` | 概念、能力模型、架构、开源参考、路线图等设计草案 |
| `doc-plugin/poc-phases/` | POC 各阶段验证记录 |
| `plugin-poc/` | 可行性验证代码，不作为生产代码直接演进 |
| `doc-plugin/development-plan/` | 生产化详细设计、开发计划、开源深度分析和集成测试计划 |

