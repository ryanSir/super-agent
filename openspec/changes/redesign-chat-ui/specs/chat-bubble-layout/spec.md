## ADDED Requirements

### Requirement: 用户消息右对齐气泡布局
用户发送的消息 SHALL 以气泡形式显示在对话区域右侧，头像在气泡右边，气泡最大宽度为容器的 72%。

#### Scenario: 用户消息右对齐显示
- **WHEN** 用户发送一条消息
- **THEN** 消息气泡出现在右侧，背景为蓝色（accent 色），文字为白色，头像在气泡右侧

#### Scenario: 长文本用户消息换行
- **WHEN** 用户消息文本超过气泡最大宽度
- **THEN** 文本自动换行，气泡高度自适应，不超过 72% 宽度限制

### Requirement: AI 消息左对齐布局
AI 回复 SHALL 以头像在左、内容在右的布局显示在对话区域左侧，内容区域宽度最大为容器的 85%。

#### Scenario: AI 消息左对齐显示
- **WHEN** AI 返回一条回复
- **THEN** AI 头像显示在左侧，内容区域在头像右侧，整体靠左对齐

#### Scenario: AI 消息包含复杂组件
- **WHEN** AI 回复包含 StepsTimeline 或 ToolResultCard 等组件
- **THEN** 这些组件在内容区域内正常渲染，不受气泡宽度限制

### Requirement: 消息时间戳显示
每条消息 SHALL 在气泡/内容区域下方显示发送时间，格式为 HH:mm。

#### Scenario: 时间戳正常显示
- **WHEN** 消息渲染完成
- **THEN** 消息下方显示 HH:mm 格式的时间，颜色为次要文字色

### Requirement: 多行输入框
输入框 SHALL 支持多行文本输入，Enter 键发送消息，Shift+Enter 换行。

#### Scenario: Enter 键发送消息
- **WHEN** 用户在输入框中按下 Enter 键（未按 Shift）
- **THEN** 消息被发送，输入框清空

#### Scenario: Shift+Enter 换行
- **WHEN** 用户在输入框中按下 Shift+Enter
- **THEN** 输入框内插入换行符，不触发发送

#### Scenario: 输入框高度自适应
- **WHEN** 用户输入多行文本
- **THEN** 输入框高度随内容自动增长，最大高度为 120px，超出后出现滚动条
