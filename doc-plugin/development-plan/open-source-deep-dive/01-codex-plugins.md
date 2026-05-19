# 01. Codex Plugins 深度分析

## 结论先行

Codex Plugins 适合作为 Plugin package layout、manifest、marketplace、enable / disable、skills / MCP / apps / hooks / assets 组合方式的强设计参考。不建议整体复用为企业平台 runtime framework，因为它更偏本地客户端和插件分发模型。

第一阶段已吸收的结论：

- 插件包采用 manifest + companion surfaces 的组合思想。OpenAI `openai/plugins` 官方仓库说明每个插件位于 `plugins/<name>/`，包含必需 `.codex-plugin/plugin.json`，并可携带 `skills/`、`.app.json`、`.mcp.json`、agents、commands、hooks、assets 等文件。
- 我们不直接照搬 `.codex-plugin/plugin.json`，而是在生产模块中使用 `plugin.yaml`，但保留“一个插件包组合多种能力”的模型。
- 第一阶段只实现 `capabilities` 列表、Skill context、HTTP/OpenAPI tool、Streamable HTTP MCP；App/UI、hooks、commands、agents 只保留后续扩展空间。

## 适用模块

- Manifest / package layout。
- Registry / Marketplace。
- Plugin install / enable / disable。
- Skill Plugin。
- MCP Plugin。
- App/UI 和 hooks 的扩展字段预留。

## 需要重点分析的问题

- `.codex-plugin/plugin.json` 的字段结构。
- `skills/`、MCP、apps、hooks、assets 如何在一个插件包中组织。
- marketplace JSON catalog 如何表达来源、安装策略、权限策略和分类。
- enable / disable 状态如何与本地配置、项目配置或用户配置关联。
- 插件 cache、版本、升级和卸载如何处理。

## 可复用点

- package layout 设计。
- manifest metadata 字段。
- marketplace catalog 思路。
- enable / disable 产品体验。
- skills / MCP / apps / hooks / assets 组合包思想。

## 不适合直接复用的点

- 本地客户端安装模型不能直接等价于企业服务端多租户模型。
- 本地 cache 和项目配置不能直接替代 workspace / agent / user 级状态。
- 凭据、权限、审计和观测需要按公司平台重新设计。

## 建议动作

- 第一阶段已输出生产版 `plugin.yaml` 的最小字段：`id`、`version`、`name`、`description`、`capabilities`。
- 第一阶段已实现本地文件版 install / enable / disable 状态，后续可替换为正式 Registry / DB。
- 后续再补 marketplace metadata、安装策略、权限策略、分类和展示素材。

## 参考来源

- [OpenAI openai/plugins 官方仓库](https://github.com/openai/plugins)
