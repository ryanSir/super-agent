# 开源深度分析目录

本目录用于保存候选开源项目的模块级深度分析。

深度分析的目标不是证明“某个项目很好”，而是帮助生产化选型：

- 哪些模块可以直接借鉴。
- 哪些模块可以局部复用。
- 哪些模块必须自研。
- 哪些项目只适合作为产品体验参考。

第一批建议分析：

| 文档 | 项目 | 关注模块 |
| --- | --- | --- |
| `01-codex-plugins.md` | Codex Plugins / openai/plugins / openai/codex | Manifest、package layout、marketplace、enable/disable |
| `02-mcpo.md` | mcpo | MCP-to-OpenAPI adapter、stdio MCP 接入 |
| `03-n8n-credential.md` | n8n | credential schema、连接测试、connector UX |
| `04-dify-plugin-daemon.md` | Dify plugin daemon | Runtime Host、daemon、debug runtime |
| `05-open-webui.md` | Open WebUI | MCP / OpenAPI / tools / pipelines 扩展分层 |
| `06-claude-code.md` | Claude Code | skills、MCP、hooks、subagents、settings、marketplace |

