"""Token 计费 — 用量追踪

TODO: 实现 per request/session/user 的 token 用量追踪
- 记录每次 LLM 调用的 input/output tokens
- 区分主 Agent 和 Sub-Agent 的用量
- 支持实时查询当前 session 累计用量
"""
