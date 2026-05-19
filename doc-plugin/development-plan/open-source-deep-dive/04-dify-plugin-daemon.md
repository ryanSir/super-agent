# 04. Dify Plugin Daemon 深度分析

## 结论先行

Dify plugin daemon 适合作为 Runtime Host、plugin runtime 生命周期、debug runtime、serverless runtime 的设计参考。由于当前阶段 Runtime Host 不一定开发，它不作为第一阶段主链路阻塞项。

## 适用模块

- Runtime Host。
- 本地或平台托管插件执行。
- runtime lifecycle。
- debug runtime。
- serverless runtime 长期方向。

## 需要重点分析的问题

- plugin daemon 如何启动、停止、健康检查和回收 runtime。
- 插件包如何被 daemon 加载。
- debug runtime 和生产 runtime 如何区分。
- serverless runtime 的调度和状态管理如何做。
- 安全隔离、资源限制、日志和事件如何实现。
- daemon 与主服务之间的通信协议是什么。

## 可复用点

- runtime lifecycle 设计。
- daemon / runtime 进程模型。
- debug runtime 体验。
- 部分接口和事件模型。

## 不适合直接复用的点

- 如果运行模型和公司部署体系不匹配，整体复用成本会很高。
- 企业 Agent 平台需要 workspace / agent / user、IAM、Credential、Audit，这些边界需要重新适配。
- Runtime Host 暂不是第一阶段必做模块，不应提前绑定复杂 daemon 框架。

## 建议动作

- 先做 P1 设计级分析。
- 只有当 stdio MCP、本地代码插件或长任务 worker 成为刚需时，再做源码级 spike。

