# 模块详细设计目录

本目录用于沉淀生产化模块详细设计。每个模块设计应说明：

- 模块职责。
- 输入输出。
- 数据模型。
- API / 接口。
- 与当前 `src_deepagent` 的集成点。
- 是否参考或复用开源项目。
- 第一阶段验收标准。

建议模块文档：

| 文档 | 模块 |
| --- | --- |
| `01-manifest-and-package.md` | Manifest、Schema、Package Layout |
| `02-registry-and-manager.md` | Registry、Plugin Manager、安装启用 |
| `03-capability-index-and-core-api.md` | Capability Index、Discovery、Invocation |
| `04-credential-policy-audit.md` | Credential、Policy、Audit |
| `05-skill-openapi-mcp-data-source.md` | Skill、OpenAPI、MCP、Data Source 能力接入 |
| `06-agent-integration.md` | 当前 `src_deepagent` 集成设计 |

