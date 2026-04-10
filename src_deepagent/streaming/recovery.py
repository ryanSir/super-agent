"""事件流 — 中断恢复 + 断点续传

TODO: 实现 SSE 连接断开后的恢复机制
- 基于 Last-Event-ID 的断点续传
- Redis Stream 消息持久化
- 客户端重连后补发丢失事件
"""
