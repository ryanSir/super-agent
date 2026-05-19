## 1. Workspace And Project Boundaries

- [x] 1.1 Create `plugin-platform/README.md` describing independent platform scope and local development commands
- [x] 1.2 Create `plugin-platform/pyproject.toml` for backend package metadata and test configuration
- [x] 1.3 Create `plugin-platform/services/plugin-core-service/plugin_core_service/__init__.py` with package version metadata
- [x] 1.4 Create `plugin-platform/services/plugin-core-service/plugin_core_service/config.py` for backend settings and storage paths
- [x] 1.5 Create `plugin-platform/tests/conftest.py` with isolated temp workspace fixtures

## 2. Manifest And Developer Lifecycle

- [x] 2.1 Create `plugin-platform/packages/plugin-contracts/plugin_contracts/manifest.py` with versioned Pydantic manifest models
- [x] 2.2 Create `plugin-platform/packages/plugin-contracts/plugin_contracts/capability.py` with capability type and summary models
- [x] 2.3 Create `plugin-platform/developer-tools/sdk/plugin_developer/validator.py` to validate `plugin.yaml` references
- [x] 2.4 Create `plugin-platform/developer-tools/sdk/plugin_developer/packager.py` to build deterministic package metadata and checksum
- [x] 2.5 Create `plugin-platform/developer-tools/sdk/plugin_developer/publisher.py` to publish packages to Registry API
- [x] 2.6 Create `plugin-platform/developer-tools/cli/pluginctl.py` exposing `validate`, `package`, and `publish` commands
- [x] 2.7 Add example plugin under `plugin-platform/examples/plugins/research-assistant/`
- [x] 2.8 Add tests for valid plugin validation, missing references, and unsupported stdio MCP

## 3. Registry And Manager Backend

- [x] 3.1 Create `plugin-platform/services/plugin-management-service/plugin_management_service/storage/repository.py` with Registry and Manager repository protocols
- [x] 3.2 Create `plugin-platform/services/plugin-management-service/plugin_management_service/storage/local_store.py` with local dev storage implementation
- [x] 3.3 Create `plugin-platform/services/plugin-management-service/plugin_management_service/registry/service.py` for publish and version lookup
- [x] 3.4 Create `plugin-platform/services/plugin-management-service/plugin_management_service/manager/service.py` for install, enable, disable, and binding state
- [x] 3.5 Create `plugin-platform/services/plugin-management-service/plugin_management_service/manager/capability_index.py` for workspace and agent indexes
- [x] 3.6 Add tests for duplicate version rejection and missing version install failure
- [x] 3.7 Add tests for enable, disable, and capability index refresh

## 4. Backend API Surface

- [x] 4.1 Create `plugin-platform/services/plugin-core-service/plugin_core_service/api/app.py` with FastAPI application factory
- [x] 4.2 Create `plugin-platform/services/plugin-core-service/plugin_core_service/api/registry_routes.py` for publish, list, and detail APIs
- [x] 4.3 Create `plugin-platform/services/plugin-core-service/plugin_core_service/api/manager_routes.py` for install, enable, disable, and bind APIs
- [x] 4.4 Create `plugin-platform/services/plugin-core-service/plugin_core_service/api/capability_routes.py` for workspace and agent capability discovery
- [x] 4.5 Create `plugin-platform/services/plugin-core-service/plugin_core_service/api/schemas.py` for API request and response DTOs
- [x] 4.6 Add API tests for publish-to-enable happy path
- [x] 4.7 Add API tests for timeout/error response shape where runtime adapters are invoked

## 5. Capability Runtime Boundary

- [x] 5.1 Create `plugin-platform/services/plugin-runtime-service/plugin_runtime_service/openapi_adapter.py` for OpenAPI invocation metadata and timeout handling
- [x] 5.2 Create `plugin-platform/services/plugin-runtime-service/plugin_runtime_service/streamable_mcp_adapter.py` for Streamable HTTP MCP JSON-RPC request handling
- [x] 5.3 Create `plugin-platform/services/plugin-runtime-service/plugin_runtime_service/skill_context.py` for structured skill context loading
- [x] 5.4 Create `plugin-platform/services/plugin-runtime-service/plugin_runtime_service/errors.py` for structured runtime errors
- [x] 5.5 Add tests for OpenAPI timeout structured errors
- [x] 5.6 Add tests for MCP JSON response and SSE content-type handling
- [x] 5.7 Add tests that Skill Context cannot be invoked as executable tool

## 6. Admin Console

- [x] 6.1 Create `plugin-platform/admin-console/package.json` with React/Vite scripts
- [x] 6.2 Create `plugin-platform/admin-console/src/api/client.ts` for backend API calls
- [x] 6.3 Create `plugin-platform/admin-console/src/types/plugin.ts` for Registry, installation, and capability types
- [x] 6.4 Create `plugin-platform/admin-console/src/App.tsx` with management console layout and routing state
- [x] 6.5 Create `plugin-platform/admin-console/src/components/PluginList.tsx` for plugin registry list
- [x] 6.6 Create `plugin-platform/admin-console/src/components/PluginDetail.tsx` for detail, versions, capabilities, and install actions
- [x] 6.7 Create `plugin-platform/admin-console/src/components/InstallStatePanel.tsx` for enable/disable/binding state
- [x] 6.8 Add frontend empty, loading, error, and API unavailable states

## 7. Open Source Deep Dive And Documentation

- [x] 7.1 Update `doc-plugin/development-plan/03-open-source-deep-dive-plan.md` with module-level reuse conclusions
- [x] 7.2 Add deep-dive notes for Codex Plugins package layout and marketplace mapping
- [x] 7.3 Add deep-dive notes for Dify manifest and plugin daemon boundaries
- [x] 7.4 Add deep-dive notes for n8n credential schema and UI implications
- [x] 7.5 Add deep-dive notes for MCP Streamable HTTP and Open WebUI transport choice
- [x] 7.6 Update `doc-plugin/development-plan/01-module-development-plan.md` with first implementation milestone

## 8. Verification

- [x] 8.1 Run platform unit tests for `plugin-platform/tests`
- [x] 8.2 Run CLI smoke test for validate/package against example plugin
- [x] 8.3 Run backend API smoke test for publish/install/enable/capability discovery
- [x] 8.4 Run admin frontend build
- [x] 8.5 Run OpenSpec status for `build-production-plugin-platform`
