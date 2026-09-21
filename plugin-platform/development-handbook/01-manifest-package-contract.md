# 01. 插件包开发手册：Manifest、目录规范、校验和发布

本文面向插件开发者和接入团队，说明如何开发一个符合 Plugin Platform 规范的插件包。

如果你只是开发插件，重点看第 1 到第 8 节。  
如果你要维护 Plugin Platform，再看第 9 节之后的内部实现说明。

## 1. 插件包交付物

接入团队需要提交一个符合平台规范的插件包。插件包以目录形式开发，以 zip 文件形式发布到 Plugin Registry。

插件包至少包含：

1. `plugin.yaml`：插件清单文件，声明插件元数据、能力、凭据和运行时信息。
2. 能力文件：例如 Skill Markdown、OpenAPI YAML、MCP 配置文件。
3. 凭据声明文件：说明插件需要哪些密钥或 token，但不包含真实密钥。
4. 可选资源文件：图标、示例、静态资源等。

最小示例：

```text
my-plugin/
  plugin.yaml
  skills/my-skill.md
  openapi/my-api.yaml
  mcp/my-mcp.yaml
  credentials/my-api-key.yaml
```

开发完成后，接入团队需要完成以下发布前动作：

```text
编写插件目录
  -> 校验 plugin.yaml 和引用文件
  -> 打包成 zip
  -> 发布到 Plugin Registry
```

平台侧会基于 `plugin.yaml` 识别插件能力，并在插件安装、启用后将能力暴露到 Capability Index。

## 2. 快速开始

先在仓库根目录设置 Python import path：

```bash
export PLUGIN_PLATFORM_PYTHONPATH="plugin-platform/packages/plugin-contracts:plugin-platform/developer-tools/cli:plugin-platform/services/plugin-management-service:plugin-platform/services/plugin-core-service:plugin-platform/services/plugin-runtime-service"
```

校验示例插件：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py validate \
  plugin-platform/examples/plugins/research-assistant
```

打包示例插件：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py package \
  plugin-platform/examples/plugins/research-assistant \
  --out plugin-platform/.artifacts/packages
```

启动本地后端：

```bash
plugin-platform/scripts/run-backend.sh
```

发布插件包：

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py publish \
  plugin-platform/.artifacts/packages/research-assistant-0.1.0.zip \
  --registry-url http://127.0.0.1:8017
```

查看 Registry：

```bash
curl http://127.0.0.1:8017/api/registry/plugins
```

## 3. 插件目录规范

插件目录必须满足：

1. 根目录必须有 `plugin.yaml`。
2. `plugin.yaml` 中声明的所有 `path` 必须指向插件目录内真实存在的文件。
3. 插件包内路径使用相对路径，例如 `skills/research-summary.md`。
4. 不要引用插件目录外部文件。
5. 发布前必须通过 `pluginctl validate`。

推荐目录：

```text
plugin-name/
  plugin.yaml
  skills/
  openapi/
  mcp/
  credentials/
  assets/
```

当前平台不会强制要求所有目录都存在。只要 `plugin.yaml` 中引用了某个文件，该文件就必须存在。

## 4. plugin.yaml 规则

示例：

```yaml
schema_version: "0.1"
plugin:
  id: research-assistant
  name: Research Assistant
  version: 0.1.0
  publisher: internal-platform
  description: Research helper capabilities for document and patent workflows.
  tags:
    - research
    - documents
capabilities:
  - type: skill
    name: research-summary
    path: skills/research-summary.md
    description: Context and usage guide for research summarization tasks.
  - type: openapi
    name: patent-search
    path: openapi/patent-search.yaml
    description: Remote patent search API capability.
mcp_servers:
  - name: literature-mcp
    path: mcp/literature.yaml
    transport: streamable-http
    endpoint: https://mcp.example.internal/literature/mcp
    description: Streamable HTTP MCP server for literature lookup.
credentials:
  - name: patent-search-api-key
    path: credentials/patent-search-api-key.yaml
    required: true
assets: []
```

字段说明：

| 字段 | 是否必填 | 规则 |
| --- | --- | --- |
| `schema_version` | 是 | 当前只支持 `"0.1"` |
| `plugin.id` | 是 | 插件唯一 ID，只允许小写字母、数字、`_`、`.`、`-` |
| `plugin.name` | 是 | 展示名称 |
| `plugin.version` | 是 | 插件版本，当前建议使用 semver，例如 `0.1.0` |
| `plugin.publisher` | 是 | 发布团队或发布方 |
| `plugin.description` | 否 | 插件说明 |
| `plugin.tags` | 否 | 标签 |
| `capabilities` | 否 | Skill / OpenAPI 能力声明 |
| `mcp_servers` | 否 | MCP Server 声明 |
| `credentials` | 否 | 凭据声明 |
| `assets` | 否 | 静态资源文件 |
| `runtime` | 否 | 运行时扩展配置，当前预留 |

## 5. 能力声明规则

### 5.1 Skill

用于声明一段可注入 Agent 上下文的技能说明。

```yaml
capabilities:
  - type: skill
    name: research-summary
    path: skills/research-summary.md
    description: Context and usage guide for research summarization tasks.
```

规则：

1. `type` 必须是 `skill`。
2. `name` 在当前插件内应保持唯一。
3. `path` 必须指向插件目录内存在的 Markdown 文件。
4. `description` 应说明这个 Skill 解决什么问题。

### 5.2 OpenAPI

用于声明一个远程 HTTP API 能力。

```yaml
capabilities:
  - type: openapi
    name: patent-search
    path: openapi/patent-search.yaml
    description: Remote patent search API capability.
```

规则：

1. `type` 必须是 `openapi`。
2. `path` 必须指向存在的 OpenAPI YAML 文件。
3. 当前阶段只校验文件存在，不做完整 OpenAPI schema 校验。

### 5.3 MCP

第一阶段只支持 Streamable HTTP MCP。

```yaml
mcp_servers:
  - name: literature-mcp
    path: mcp/literature.yaml
    transport: streamable-http
    endpoint: https://mcp.example.internal/literature/mcp
    description: Streamable HTTP MCP server for literature lookup.
```

规则：

1. `transport` 必须是 `streamable-http`。
2. 当前阶段不支持 `stdio`。
3. `endpoint` 必须填写远程 MCP 服务地址。
4. `path` 必须指向存在的 MCP 配置文件。

## 6. 凭据声明规则

凭据声明用于告诉平台这个插件需要哪些密钥或 token。

```yaml
credentials:
  - name: patent-search-api-key
    path: credentials/patent-search-api-key.yaml
    required: true
```

当前阶段只校验 `path` 文件存在，还没有接入正式 Credential Broker 和公司密钥系统。

建议规则：

1. 不要把真实密钥写进插件包。
2. `credentials/*.yaml` 只写凭据名称、用途、注入方式等声明信息。
3. 后续真实密钥应由平台密钥系统绑定。

## 7. 校验、打包、发布

### 7.1 校验

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py validate \
  path/to/my-plugin
```

校验会检查：

1. 是否存在 `plugin.yaml`。
2. `schema_version` 是否支持。
3. `plugin.id` 等字段格式是否正确。
4. manifest 中引用的文件是否存在。
5. MCP transport 是否为 `streamable-http`。

### 7.2 打包

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py package \
  path/to/my-plugin \
  --out plugin-platform/.artifacts/packages
```

打包规则：

1. 打包前会自动执行校验。
2. 校验失败不会生成可发布 zip。
3. zip 文件名为 `{plugin.id}-{plugin.version}.zip`。
4. 打包完成后会返回 sha256 checksum。

### 7.3 发布

```bash
PYTHONPATH="$PLUGIN_PLATFORM_PYTHONPATH" \
python plugin-platform/developer-tools/cli/pluginctl.py publish \
  plugin-platform/.artifacts/packages/my-plugin-0.1.0.zip \
  --registry-url http://127.0.0.1:8017
```

发布成功后，Registry 会返回：

```json
{
  "plugin_id": "my-plugin",
  "version": "0.1.0",
  "checksum": "...",
  "status": "published"
}
```

## 8. 常见错误

| 错误码 / 异常 | 原因 | 处理方式 |
| --- | --- | --- |
| `manifest_missing` | 缺少 `plugin.yaml` | 在插件根目录补充 `plugin.yaml` |
| `manifest_invalid` | manifest 字段格式不符合规则 | 根据错误信息修正字段 |
| `referenced_file_missing` | `path` 指向的文件不存在 | 修正路径或补齐文件 |
| `unsupported_mcp_transport` | 使用了 `stdio` MCP | 改成 `streamable-http` |
| `PackageError` | 打包前校验失败 | 先执行 validate 并修复问题 |
| `PublishError` | 发布失败、超时或包不存在 | 检查 Registry 地址、网络和 zip 路径 |

## 9. 插件提交前检查清单

提交给平台前，请确认：

- `plugin.yaml` 位于插件根目录。
- `schema_version` 是 `"0.1"`。
- `plugin.id` 稳定且唯一。
- `plugin.version` 已按本次变更递增。
- 所有 `path` 都是相对路径。
- 所有引用文件都已放进插件目录。
- 没有真实密钥进入插件包。
- MCP 使用 `streamable-http`。
- `pluginctl validate` 成功。
- `pluginctl package` 成功。

## 10. 内部代码入口

这部分给 Plugin Platform 维护者看。

| 代码 | 职责 |
| --- | --- |
| `packages/plugin-contracts/plugin_contracts/manifest.py` | 定义 `PluginManifest`、`PluginMetadata`、MCP 和凭据结构 |
| `packages/plugin-contracts/plugin_contracts/capability.py` | 定义 `CapabilityType`、`CapabilityRef`、`CapabilitySummary`、校验结果结构 |
| `developer-tools/cli/pluginctl.py` | CLI 入口，暴露 validate / package / publish 命令 |
| `packages/plugin-contracts/plugin_contracts/validation.py` | 校验插件目录和生成能力摘要，供 CLI 和 Registry 共用 |
| `developer-tools/cli/plugin_cli/packager.py` | 打包校验通过的插件目录并生成 checksum |
| `developer-tools/cli/plugin_cli/publisher.py` | 把 zip 包发布到 Registry API |

## 11. 内部执行流程

校验流程：

```text
pluginctl.py
  -> validate_plugin(plugin_dir)
    -> load_manifest(plugin_dir)
      -> PluginManifest.model_validate(...)
    -> _validate_referenced_files(...)
    -> _validate_mcp_transports(...)
    -> _build_capability_summary(...)
```

打包流程：

```text
pluginctl.py
  -> package_plugin(plugin_dir, output_dir)
    -> validate_plugin(plugin_dir)
    -> load_manifest(plugin_dir)
    -> ZipFile(...)
    -> _file_sha256(...)
```

发布流程：

```text
pluginctl.py
  -> publish_package(registry_url, package_path)
    -> POST /api/registry/packages
```

## 12. 测试和验收

测试文件：

```text
plugin-platform/tests/test_developer_lifecycle.py
```

运行：

```bash
python -m pytest plugin-platform/tests/test_developer_lifecycle.py
```

覆盖场景：

- 示例插件校验成功。
- 缺失引用文件时报错。
- stdio MCP 在第一阶段被拒绝。
- 打包成功并生成 checksum。
- 校验失败时打包中断。

## 13. 当前阶段边界

当前已支持：

- manifest 结构校验。
- 引用文件存在性校验。
- Skill / OpenAPI / Streamable HTTP MCP 声明。
- 插件 zip 打包。
- 发布到 Registry API。

当前暂不支持：

- 完整 OpenAPI schema 校验。
- stdio MCP。
- 真实 Credential Broker。
- 权限策略校验。
- 审计和观测。
- 多语言 SDK。
