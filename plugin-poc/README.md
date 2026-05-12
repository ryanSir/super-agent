# Plugin POC

This directory contains the Plugin POC for validating the plugin lifecycle from packaging to Agent-facing capability consumption.

## Commands

Run commands from this directory:

```bash
python -m plugin_poc.cli validate examples/slack-demo
python -m plugin_poc.cli package examples/slack-demo --output dist
python -m plugin_poc.cli publish examples/slack-demo --registry .plugin-registry --force
```

Usage docs:

- [poc-acceptance-and-roadmap.md](./poc-acceptance-and-roadmap.md): POC 验收说明、流程图映射、部署边界和生产化 Roadmap
- [code-structure-and-deployment-mapping.md](./code-structure-and-deployment-mapping.md): 代码分层、泳道图映射和未来服务边界
- [phase-1-packaging-registry.md](./phase-1-packaging-registry.md): validate, package, publish
- [phase-2-install-enable-capabilities.md](./phase-2-install-enable-capabilities.md): install, enable, capability index
- [phase-3-tool-invocation-gateway.md](./phase-3-tool-invocation-gateway.md): invoke enabled tool capability
- [phase-4-credential-policy-audit.md](./phase-4-credential-policy-audit.md): credential, policy check, audit log
- [phase-5-openapi-runtime.md](./phase-5-openapi-runtime.md): invoke OpenAPI capability with mock runtime
- [phase-6-mcp-runtime.md](./phase-6-mcp-runtime.md): invoke Streamable HTTP MCP endpoint
- [phase-7-skill-runtime.md](./phase-7-skill-runtime.md): load plugin skills and render Agent context
- [phase-8-data-source-runtime.md](./phase-8-data-source-runtime.md): query data source capabilities
- [phase-9-runtime-host-stdio-adapter.md](./phase-9-runtime-host-stdio-adapter.md): runtime host and stdio adapter metadata
- [phase-10-observability-runtime-hardening.md](./phase-10-observability-runtime-hardening.md): runtime events and timeout handling
- [phase-11-e2e-acceptance.md](./phase-11-e2e-acceptance.md): local end-to-end acceptance command

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
