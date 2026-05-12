# Plugin POC Phase 1 使用说明

## 当前能力

Phase 1 已实现插件开发到发布的最小闭环：

```text
validate -> package -> publish
```

当前可以验证：

- `plugin.yaml` 是否合法。
- `plugin.yaml` 引用的子文件是否存在。
- 插件是否能被打包成 zip。
- 插件包是否包含 `package.json` 和 `checksums.json`。
- 插件是否能发布到本地文件型 Registry。
- Registry 是否记录插件 id、version、checksum 和包路径。

当前还不支持：

- install
- enable / disable
- credential 配置
- capability index
- Agent 调用插件
- MCP/OpenAPI 真实执行

这些属于 Phase 2 及后续阶段。

## 目录结构

```text
plugin-poc/
├── README.md
├── phase-1-packaging-registry.md
├── plugin_poc/
│   ├── __init__.py
│   ├── cli.py
│   ├── errors.py
│   ├── io.py
│   ├── models.py
│   ├── validator.py
│   ├── packager.py
│   └── publisher.py
├── schemas/
│   └── plugin.schema.json
├── examples/
│   └── slack-demo/
│       ├── plugin.yaml
│       ├── tools/
│       │   └── slack-tools.yaml
│       ├── skills/
│       │   └── summarize-channel/
│       │       └── SKILL.md
│       ├── openapi/
│       │   └── slack.yaml
│       ├── credentials/
│       │   └── oauth.yaml
│       └── data_sources/
│           └── slack-messages.yaml
└── tests/
    └── test_plugin_poc.py
```

### 根文件

| 文件 | 作用 |
| --- | --- |
| `README.md` | POC 简介和最短命令入口 |
| `phase-1-packaging-registry.md` | 当前文档，说明 Phase 1 插件校验、打包和本地 Registry 发布如何使用和验证 |

### `plugin_poc/` 核心代码

| 文件 | 作用 |
| --- | --- |
| `plugin_poc/__init__.py` | 包入口，导出 `validate_plugin`、`build_package`、`publish_plugin` 等核心函数 |
| `plugin_poc/cli.py` | CLI 入口，提供 `validate`、`package`、`publish` 三个命令 |
| `plugin_poc/errors.py` | 统一异常定义，包括 `ValidationError`、`PackageError`、`PublishError` |
| `plugin_poc/io.py` | 文件读写工具，包括 YAML/JSON 读写和 sha256 计算 |
| `plugin_poc/models.py` | 数据结构定义，包括 `ValidationResult`、`PackageResult`、`PublishResult` |
| `plugin_poc/validator.py` | 插件校验逻辑，读取 `plugin.yaml`，校验必填字段、枚举、版本号和子文件路径 |
| `plugin_poc/packager.py` | 插件打包逻辑，生成 zip 包、`package.json`、`checksums.json` 和外部 metadata |
| `plugin_poc/publisher.py` | 本地 Registry 发布逻辑，把插件包写入 registry 目录并更新 `index.json` |

### `schemas/` 规范文件

| 文件 | 作用 |
| --- | --- |
| `schemas/plugin.schema.json` | 第一版 manifest schema 占位规范。当前校验逻辑主要在 Python 代码中实现，后续可切换为正式 JSON Schema 校验 |

### `examples/slack-demo/` 示例插件

| 文件 | 作用 |
| --- | --- |
| `examples/slack-demo/plugin.yaml` | 示例插件 manifest，声明插件身份、capabilities、auth、permissions、runtime、policy、observability |
| `examples/slack-demo/tools/slack-tools.yaml` | 示例 Tool 能力，声明 `send_message` 的输入 schema |
| `examples/slack-demo/skills/summarize-channel/SKILL.md` | 示例 Skill，描述如何总结频道消息 |
| `examples/slack-demo/openapi/slack.yaml` | 示例 OpenAPI spec，用于验证 OpenAPI capability 引用 |
| `examples/slack-demo/credentials/oauth.yaml` | 示例 OAuth credential schema，用于验证凭据配置引用 |
| `examples/slack-demo/data_sources/slack-messages.yaml` | 示例 data source 声明，用于验证数据源能力引用 |

### `tests/` 测试文件

| 文件 | 作用 |
| --- | --- |
| `tests/test_plugin_poc.py` | 覆盖 manifest 校验、缺字段错误、缺子文件错误、打包、发布、重复发布保护和 CLI 命令 |

### 运行后生成的目录

这些目录不是源码，通常不需要提交：

| 目录 | 何时生成 | 作用 |
| --- | --- | --- |
| `/tmp/plugin-poc-dist` | 执行 `package --output /tmp/plugin-poc-dist` 后生成 | 保存本次打包出的 zip 和 metadata |
| `/tmp/plugin-poc-registry` | 执行 `publish --registry /tmp/plugin-poc-registry` 后生成 | 本地文件型 Registry，保存插件包、manifest snapshot、metadata 和 `index.json` |
| `__pycache__/` | Python 运行或编译后生成 | Python 字节码缓存，可忽略 |

## 使用前提

从仓库根目录执行命令：

```bash
cd /Users/zhangyang/Desktop/temp/super-agent
```

命令前需要加 `PYTHONPATH=plugin-poc`，让 Python 能找到 `plugin_poc` 模块：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli --help
```

## 1. 校验插件

命令：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate plugin-poc/examples/slack-demo
```

预期输出：

```json
{
  "status": "ok",
  "plugin_id": "company.slack-demo",
  "version": "1.0.0",
  "referenced_files": [
    "credentials/oauth.yaml",
    "data_sources/slack-messages.yaml",
    "openapi/slack.yaml",
    "skills/summarize-channel/SKILL.md",
    "tools/slack-tools.yaml"
  ]
}
```

这个命令会检查：

- `plugin.yaml` 是否存在。
- 必填字段是否存在：`schema_version`、`id`、`name`、`version`、`capabilities`。
- `version` 是否符合 `MAJOR.MINOR.PATCH`。
- `capabilities` 至少包含一种能力。
- tools、skills、openapi、credentials、data_sources 引用的文件是否存在。
- `auth.type`、`runtime.mode`、`mcp.transport` 是否在允许范围内。

## 2. 打包插件

命令：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli package plugin-poc/examples/slack-demo --output /tmp/plugin-poc-dist
```

预期输出会包含：

```json
{
  "plugin_id": "company.slack-demo",
  "version": "1.0.0",
  "package_path": "/private/tmp/plugin-poc-dist/company.slack-demo-1.0.0.zip",
  "metadata_path": "/private/tmp/plugin-poc-dist/company.slack-demo-1.0.0.metadata.json",
  "checksum": "..."
}
```

查看打包结果：

```bash
ls -l /tmp/plugin-poc-dist
```

预期包含：

```text
company.slack-demo-1.0.0.zip
company.slack-demo-1.0.0.metadata.json
```

查看 zip 内容：

```bash
unzip -l /tmp/plugin-poc-dist/company.slack-demo-1.0.0.zip
```

预期包含：

```text
plugin.yaml
package.json
checksums.json
tools/slack-tools.yaml
skills/summarize-channel/SKILL.md
openapi/slack.yaml
credentials/oauth.yaml
data_sources/slack-messages.yaml
```

说明：

- `package.json` 是打包时生成的插件包元数据。
- `checksums.json` 是包内文件 checksum。
- zip 包使用稳定时间戳，方便得到稳定 checksum。

## 3. 发布到本地 Registry

命令：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo --registry /tmp/plugin-poc-registry --force
```

预期输出：

```json
{
  "plugin_id": "company.slack-demo",
  "version": "1.0.0",
  "registry_dir": "/private/tmp/plugin-poc-registry",
  "package_path": "/private/tmp/plugin-poc-registry/packages/company.slack-demo/1.0.0/package.zip",
  "metadata_path": "/private/tmp/plugin-poc-registry/packages/company.slack-demo/1.0.0/metadata.json",
  "index_path": "/private/tmp/plugin-poc-registry/index.json",
  "checksum": "..."
}
```

查看 Registry 结构：

```bash
find /tmp/plugin-poc-registry -maxdepth 5 -type f | sort
```

预期结构：

```text
/tmp/plugin-poc-registry/index.json
/tmp/plugin-poc-registry/packages/company.slack-demo/1.0.0/manifest.yaml
/tmp/plugin-poc-registry/packages/company.slack-demo/1.0.0/metadata.json
/tmp/plugin-poc-registry/packages/company.slack-demo/1.0.0/package.zip
```

查看 Registry index：

```bash
cat /tmp/plugin-poc-registry/index.json
```

`index.json` 会记录：

- plugin id
- version
- name
- description
- author
- checksum
- package path
- metadata path
- published time

## 4. 验证重复发布保护

第一次发布：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo --registry /tmp/plugin-poc-registry --force
```

第二次不加 `--force`：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli publish plugin-poc/examples/slack-demo --registry /tmp/plugin-poc-registry
```

预期失败：

```json
{
  "status": "error",
  "errors": [
    "plugin version already exists: company.slack-demo@1.0.0"
  ]
}
```

## 5. 验证非法插件

可以复制示例插件后手动破坏一个字段：

```bash
cp -R plugin-poc/examples/slack-demo /tmp/slack-demo-invalid
```

删除一个被引用的子文件：

```bash
rm /tmp/slack-demo-invalid/tools/slack-tools.yaml
```

再次校验：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate /tmp/slack-demo-invalid
```

预期失败：

```json
{
  "status": "error",
  "errors": [
    "capabilities.tools[0].path points to missing file: tools/slack-tools.yaml"
  ]
}
```

## 6. 运行测试

当前环境默认 pytest capture 可能触发 Python segfault，因此使用 `-p no:capture`。

命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=plugin-poc python -m pytest -p no:capture plugin-poc/tests/test_plugin_poc.py -q
```

预期结果：

```text
7 passed
```

运行 ruff：

```bash
ruff check plugin-poc
```

预期结果：

```text
All checks passed!
```

运行编译检查：

```bash
PYTHONPATH=plugin-poc python -m compileall -q plugin-poc/plugin_poc plugin-poc/tests
```

无输出表示通过。

## 7. 常见问题

### ModuleNotFoundError: No module named plugin_poc

原因：没有设置 `PYTHONPATH`。

解决：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli validate plugin-poc/examples/slack-demo
```

### publish 后示例目录里没有 dist 文件

这是预期行为。

`publish` 命令会使用临时目录打包，然后把结果写入 Registry，不会污染示例插件目录。

如果需要保留包文件，请单独运行：

```bash
PYTHONPATH=plugin-poc python -m plugin_poc.cli package plugin-poc/examples/slack-demo --output /tmp/plugin-poc-dist
```

### 当前怎么启用插件

Phase 1 暂不支持启用。

当前流程停在：

```text
validate -> package -> publish
```

启用属于 Phase 2，需要实现：

```text
install -> configure -> enable -> write Capability Index
```
