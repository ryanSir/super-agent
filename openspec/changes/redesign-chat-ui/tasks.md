## 1. 头像资源

- [x] 1.1 在 `frontend/src/assets/avatars.ts` 中定义用户头像 SVG Data URI 常量 `USER_AVATAR`（渐变蓝紫色圆形，人物轮廓）
- [x] 1.2 在 `frontend/src/assets/avatars.ts` 中定义 AI 头像 SVG Data URI 常量 `AI_AVATAR`（渐变青蓝色圆形，AI 风格图形）

## 2. ChatMessage 组件重构

- [x] 2.1 修改 `frontend/src/components/ChatMessage.tsx`：用户消息使用 `USER_AVATAR` 图片，头像移至右侧，气泡右对齐
- [x] 2.2 修改 `frontend/src/components/ChatMessage.tsx`：AI 消息使用 `AI_AVATAR` 图片，头像在左侧，内容区域在右侧
- [x] 2.3 在 `ChatMessage.tsx` 中添加时间戳显示（HH:mm 格式，显示在消息下方）

## 3. App.tsx 输入框升级

- [x] 3.1 将 `frontend/src/App.tsx` 中的 `<input type="text">` 替换为 `<textarea>`
- [x] 3.2 在 `App.tsx` 中添加 `onKeyDown` 处理：Enter 发送，Shift+Enter 换行
- [x] 3.3 在 `App.tsx` 中添加 `onInput` 处理：textarea 高度随内容自适应，最大高度 120px

## 4. CSS 样式重写

- [x] 4.1 在 `frontend/src/styles/globals.css` 中重写 `.message-row`：用户消息行 `justify-content: flex-end`，AI 消息行 `justify-content: flex-start`
- [x] 4.2 在 `globals.css` 中添加用户气泡样式 `.chat-message-user`：蓝色背景、白色文字、圆角、最大宽度 72%
- [x] 4.3 在 `globals.css` 中添加 AI 消息样式 `.chat-message-assistant`：头像+内容并排，内容区最大宽度 85%
- [x] 4.4 在 `globals.css` 中更新头像样式 `.message-avatar`：36x36px 圆形图片，`object-fit: cover`
- [x] 4.5 在 `globals.css` 中添加 textarea 输入框样式：自适应高度、最大高度 120px、resize none
- [x] 4.6 在 `globals.css` 中添加消息时间戳样式 `.message-timestamp`：12px、次要文字色、右对齐（用户）/左对齐（AI）

## 5. 主题切换

- [x] 5.1 在 `frontend/src/App.tsx` 中添加 `theme` state（默认 `'dark'`），从 localStorage 读取初始值
- [x] 5.2 在 `App.tsx` 的 `useEffect` 中将 `data-theme` 属性同步到 `document.documentElement`，并写入 localStorage
- [x] 5.3 在 Header 中添加主题切换按钮，暗色时显示 ☀️ 图标，亮色时显示 🌙 图标
- [x] 5.4 在 `globals.css` 中添加 `[data-theme="light"]` 选择器，覆盖所有 CSS 变量为亮色配色（白底深字）

## 6. 基础品质提升

- [x] 6.1 修改 `frontend/index.html`：添加 `<title>Super Agent</title>`、SVG inline favicon、`meta description`、`theme-color` meta 标签
- [x] 6.2 在 `globals.css` 的 `:root` 中补充 design token：`--shadow-sm`、`--shadow-md`、`--transition-fast`（0.15s ease）、`--transition-base`（0.2s ease）
- [x] 6.3 在 `globals.css` 中添加自定义滚动条样式（`::-webkit-scrollbar` 系列，宽度 6px，圆角，颜色跟随主题变量）
- [x] 6.4 在 `globals.css` 中添加消息入场动画 `@keyframes msgIn`（fade + translateY 8px → 0），应用到 `.message-row`

## 7. Markdown 渲染增强

- [x] 7.1 在 `frontend/package.json` 中添加依赖：`remark-gfm`、`rehype-highlight`、`highlight.js`
- [x] 7.2 在 `ResponseBlock.tsx` 和 `ChatMessage.tsx` 中为 `<ReactMarkdown>` 添加 `remarkPlugins={[remarkGfm]}` 和 `rehypePlugins={[rehypeHighlight]}`
- [x] 7.3 在 `ResponseBlock.tsx` 中为代码块添加复制按钮：自定义 `components.pre`，hover 时右上角显示复制图标，点击后 2s 内显示"已复制"反馈
- [x] 7.4 在 `globals.css` 中添加代码高亮主题样式（暗色用 github-dark 风格，亮色用 github 风格，通过 `[data-theme]` 切换）

## 8. 交互细节

- [x] 8.1 在 `App.tsx` 输入框下方添加提示文字：`Enter 发送 · Shift+Enter 换行`，颜色为次要文字色，字号 12px
- [x] 8.2 在 `App.tsx` 空状态区域替换现有标题，添加品牌 SVG logo 图标 + 欢迎标语（"有什么我可以帮你的？"）
- [x] 8.3 在 `ChatMessage.tsx` 用户气泡上添加 hover 时显示的复制按钮，点击复制消息文本到剪贴板
