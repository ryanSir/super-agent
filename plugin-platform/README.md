# Plugin Platform

独立 Plugin 平台工作区。这里承载生产级 Plugin 平台的开发者工具、平台管理服务、Plugin 核心服务、插件运行时服务、管理平台前端、示例插件和测试代码。

当前仓库仍然是 Agent 项目，`plugin-platform/` 只是为了本地开发和联调放在同一个仓库中。Plugin 平台代码不得依赖或修改 `src_deepagent`，后续可以迁移到独立项目或拆成多个部署单元。

## Modules

- `developer-tools/`: 插件开发者 CLI / SDK。
- `services/plugin-management-service/`: Registry、Plugin Manager、Capability Index 状态管理。
- `services/plugin-core-service/`: FastAPI app、管理 API、Capability Discovery API。
- `services/plugin-runtime-service/`: OpenAPI、Streamable HTTP MCP、Skill Context runtime adapter。
- `packages/plugin-contracts/`: manifest、capability 等共享契约。
- `admin-console/`: Plugin 管理平台前端。
- `examples/`: 示例插件。
- `tests/`: 平台级单测和流程测试。

## Local Commands

```bash
python -m pytest plugin-platform/tests

export PLUGIN_PLATFORM_PYTHONPATH="plugin-platform/packages/plugin-contracts:plugin-platform/developer-tools/sdk:plugin-platform/services/plugin-management-service:plugin-platform/services/plugin-core-service:plugin-platform/services/plugin-runtime-service"

PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py validate \
  plugin-platform/examples/plugins/research-assistant

PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py package \
  plugin-platform/examples/plugins/research-assistant \
  --out /tmp/plugin-packages
```

第一阶段优先打通开发、校验、打包、发布、安装、启用和能力索引链路。当前 Agent 集成、完整权限、凭据托管、审计、stdio MCP adapter 和 Runtime Host 均放到后续阶段。

本地启动也可以直接使用脚本：

```bash
plugin-platform/scripts/run-backend.sh
plugin-platform/scripts/run-admin-console.sh
```

更完整的目录映射、测试方式和本地启动链路见 [RUNBOOK.md](RUNBOOK.md)。
