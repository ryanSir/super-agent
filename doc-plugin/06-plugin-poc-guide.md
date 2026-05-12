# Plugin POC 使用指南

本文说明当前 Plugin POC 的基本使用方式，并索引各阶段操作文档。POC 代码仍保留在 `../plugin-poc` 目录，本目录只集中存放说明文档。

## Commands

在项目根目录执行：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate plugin-poc/examples/slack-demo
PYTHONPATH=plugin-poc python -m plugin_poc.cli package plugin-poc/examples/slack-demo --output /tmp/plugin-poc-dist
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo --registry /tmp/plugin-poc-registry --force
```

Usage docs:

- [04-poc-acceptance-and-roadmap.md](./04-poc-acceptance-and-roadmap.md): POC 验收说明、流程图映射、部署边界和生产化 Roadmap
- [05-code-structure-and-deployment-mapping.md](./05-code-structure-and-deployment-mapping.md): 代码分层、泳道图映射和未来服务边界
- [poc-phases/phase-1-packaging-registry.md](./poc-phases/phase-1-packaging-registry.md): validate, package, publish
- [poc-phases/phase-2-install-enable-capabilities.md](./poc-phases/phase-2-install-enable-capabilities.md): install, enable, capability index
- [poc-phases/phase-3-tool-invocation-gateway.md](./poc-phases/phase-3-tool-invocation-gateway.md): invoke enabled tool capability
- [poc-phases/phase-4-credential-policy-audit.md](./poc-phases/phase-4-credential-policy-audit.md): credential, policy check, audit log
- [poc-phases/phase-5-openapi-runtime.md](./poc-phases/phase-5-openapi-runtime.md): invoke OpenAPI capability with mock runtime
- [poc-phases/phase-6-mcp-runtime.md](./poc-phases/phase-6-mcp-runtime.md): invoke Streamable HTTP MCP endpoint
- [poc-phases/phase-7-skill-runtime.md](./poc-phases/phase-7-skill-runtime.md): load plugin skills and render Agent context
- [poc-phases/phase-8-data-source-runtime.md](./poc-phases/phase-8-data-source-runtime.md): query data source capabilities
- [poc-phases/phase-9-runtime-host-stdio-adapter.md](./poc-phases/phase-9-runtime-host-stdio-adapter.md): runtime host and stdio adapter metadata
- [poc-phases/phase-10-observability-runtime-hardening.md](./poc-phases/phase-10-observability-runtime-hardening.md): runtime events and timeout handling
- [poc-phases/phase-11-e2e-acceptance.md](./poc-phases/phase-11-e2e-acceptance.md): local end-to-end acceptance command

## Completed POC Scope

- `plugin.yaml` validation
- child file path validation
- zip package generation
- metadata and checksum generation
- local file registry publishing
- install, enable, disable and uninstall
- workspace/agent scoped capability index
- tool invocation gateway
- credential configuration, policy check and audit log
- mock OpenAPI runtime
- Streamable HTTP MCP runtime
- plugin skill loading and Agent context rendering
- local JSON data source runtime
- runtime host lifecycle state and stdio adapter registration
- runtime event logs and timeout handling
- local end-to-end acceptance command
