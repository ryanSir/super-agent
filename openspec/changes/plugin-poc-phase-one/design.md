## Context

当前仓库是 Agent POC 项目，已有 `doc-plugin/07-development-plan-and-estimation.md` 描述 Plugin 0-1 开发节奏。第一期开发不应直接改造现有 Agent 主链路，而是在当前仓库新增独立 `plugin-poc/` 子目录，先完成插件规范、打包和本地 Registry 的闭环。

本期属于 Plugin 平台的基础设施 POC，后续 Plugin Manager、Runtime Host、Capability Resolver 和 Tool Invocation Gateway 会基于本期产物继续演进。

## Goals / Non-Goals

**Goals:**

- 建立 `plugin-poc/` 独立目录，便于后续拆分为独立工程。
- 提供 `plugin.yaml` 第一版 schema 和校验器。
- 支持子配置引用校验，包括 tools、skills、credentials、openapi、data_sources。
- 提供插件包格式，生成 zip、manifest snapshot、metadata 和 checksums。
- 提供本地文件型 Registry，支持发布和查询插件版本。
- 提供 CLI 入口，跑通 `validate`、`package`、`publish`。
- 提供示例插件和测试，验证第一期闭环。

**Non-Goals:**

- 不实现真实插件执行 runtime。
- 不实现 Agent Runtime 调用插件。
- 不实现远程 Registry 服务。
- 不实现 OAuth 完整授权流程。
- 不实现插件签名、安全扫描、SBOM 和依赖锁定。

## Decisions

### Decision 1: 在当前仓库新建 `plugin-poc/`，不直接改 `src_deepagent/`

原因：当前目标是验证 Plugin 基础闭环和现有 Agent 系统的接入边界。放在当前仓库可以共享上下文和测试环境，同时保持目录隔离，避免过早污染主 Agent Runtime。

备选方案：

- 新开工程：隔离更强，但不利于验证和现有 Agent 的接入关系。
- 直接加入 `src_deepagent/`：接入更快，但会提高主系统侵入性。

### Decision 2: 使用 Python 标准库 + PyYAML 实现第一版 CLI

原因：仓库根依赖已有 `python-dotenv` 等 Python 基础栈，且 PyYAML 在当前环境可用。第一期优先减少新依赖，不引入 Typer/Click/jsonschema 等额外包。schema 校验先实现为代码级结构校验，后续再补 `plugin.schema.json` 和 JSON Schema validator。

备选方案：

- 使用 Click/Typer：CLI 体验更好，但会增加依赖。
- 使用 jsonschema：校验表达更标准，但第一期可先用轻量校验器跑通闭环。

### Decision 3: 第一版 Registry 使用本地文件存储

原因：Phase 1 目标是验证发布和版本管理，不需要服务化 Registry。文件型 Registry 便于测试和迁移，后续可替换为数据库或对象存储。

本地 Registry 结构：

```text
.plugin-registry/
├── index.json
└── packages/
    └── <plugin_id>/
        └── <version>/
            ├── package.zip
            ├── metadata.json
            └── manifest.yaml
```

### Decision 4: 插件包采用 zip 格式

原因：zip 是跨平台标准格式，Python 标准库直接支持，适合第一期验证。包内必须包含 `plugin.yaml`、`package.json`、`checksums.json` 和被 manifest 引用的子文件。

后续可扩展：

- 签名文件
- SBOM
- 依赖锁文件
- 安全扫描结果

## Risks / Trade-offs

- [Risk] 代码级 schema 校验不如 JSON Schema 标准化 → 第一版保留 `schemas/plugin.schema.json` 文件，后续可切换为正式 JSON Schema validator。
- [Risk] 本地文件 Registry 不能表达并发发布和权限治理 → 第一版仅用于 POC，后续 Registry 服务化时复用 metadata 格式。
- [Risk] package 命令可能误打包临时文件 → 第一版跳过 `.plugin-registry`、`__pycache__`、`.DS_Store` 和输出目录，后续支持 `.pluginignore`。
- [Risk] CLI 和平台 API 边界尚未稳定 → 先把核心能力放在 Python 模块中，CLI 只做薄封装。

## Migration Plan

本期为新增独立目录，无现有数据迁移。

回滚方式：

- 删除 `plugin-poc/`
- 删除 `openspec/changes/plugin-poc-phase-one/`
- 不影响现有 Agent POC 运行。

## Open Questions

- 后续是否将 `plugin-poc/` 拆为独立仓库或 Python package。
- `plugin.schema.json` 是否在 Phase 2 切换为正式 JSON Schema 校验。
- Registry 后续复用内部制品仓库，还是自建服务。
- 插件包是否需要从第一版之后引入签名和 SBOM。
