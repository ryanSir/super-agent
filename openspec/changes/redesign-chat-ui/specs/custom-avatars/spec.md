## ADDED Requirements

### Requirement: 用户头像图片
用户消息 SHALL 使用精美的自定义 SVG 头像图片，不使用 emoji 字符。头像为圆形，尺寸 36x36px。

#### Scenario: 用户头像正常显示
- **WHEN** 用户消息渲染
- **THEN** 右侧显示圆形用户头像图片，背景为渐变蓝紫色，包含人物轮廓图形

#### Scenario: 头像尺寸一致
- **WHEN** 多条用户消息连续显示
- **THEN** 所有用户头像尺寸统一为 36x36px，垂直居中对齐消息顶部

### Requirement: AI 头像图片
AI 消息 SHALL 使用精美的自定义 SVG 头像图片，不使用 emoji 字符。头像为圆形，尺寸 36x36px。

#### Scenario: AI 头像正常显示
- **WHEN** AI 消息渲染
- **THEN** 左侧显示圆形 AI 头像图片，背景为渐变青蓝色，包含 AI/机器人风格图形

#### Scenario: 流式输出时头像稳定显示
- **WHEN** AI 正在流式输出内容
- **THEN** AI 头像保持稳定显示，不随内容更新而闪烁
