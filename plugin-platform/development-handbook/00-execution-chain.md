# 00. Plugin Platform 统一执行链路

本文只保留全局入口。详细执行链路放到每个阶段文档里，学习某个阶段时直接看对应文档。

## 1. 全局主链路

```text
开发插件目录
  -> validate
  -> package
  -> publish 到 Registry
  -> install
  -> enable
  -> capability discovery
  -> Admin Console 查看状态
```

## 2. 执行方式

执行入口放到每个阶段文档里。需要后端时，统一先启动：

```bash
plugin-platform/scripts/run-backend.sh
```

## 3. 阶段文档索引

| 阶段 | 文档 | 执行链路 |
| --- | --- |
| M1 | `01-manifest-package-contract.md` | validate / package / publish |
| M2 | `02-install-enable-capability-index.md` | install / enable / capability discovery |
| M3 | `03-runtime-loading-boundary.md` | runtime loading boundary |
| M3 | 待补 | capability discovery / Admin Console |
