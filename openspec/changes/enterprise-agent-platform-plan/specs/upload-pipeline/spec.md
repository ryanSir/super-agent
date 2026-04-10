## ADDED Requirements

### Requirement: markitdown 文件转换管线
系统 SHALL 支持 PDF / Excel / Word / PPT 文件上传并转换为 Markdown 格式，使用 markitdown 库处理。转换结果 SHALL 保留原文档的结构（标题、表格、列表）。

#### Scenario: PDF 转换
- **WHEN** 用户上传 PDF 文件
- **THEN** 系统 SHALL 提取文本和表格，转换为 Markdown，保留标题层级

#### Scenario: Excel 转换
- **WHEN** 用户上传 Excel 文件（含多个 Sheet）
- **THEN** 系统 SHALL 将每个 Sheet 转换为 Markdown 表格，Sheet 名作为二级标题

#### Scenario: 不支持的文件类型
- **WHEN** 用户上传 .exe 或 .zip 文件
- **THEN** 系统 SHALL 返回错误 "不支持的文件类型"，不进行处理

#### Scenario: 大文件处理
- **WHEN** 上传文件超过 50MB
- **THEN** 系统 SHALL 拒绝上传并返回文件大小超限错误

### Requirement: 分片上传 + 进度追踪
系统 SHALL 支持大文件分片上传（每片 5MB），上传过程中 SHALL 推送进度事件到前端。

#### Scenario: 分片上传
- **WHEN** 用户上传 30MB 文件
- **THEN** 系统 SHALL 分 6 片上传，每片完成后推送 upload_progress 事件（含百分比）

#### Scenario: 断点续传
- **WHEN** 上传过程中网络中断
- **THEN** 客户端重连后 SHALL 从最后成功的分片继续上传，不重传已完成部分

### Requirement: 文件安全扫描
系统 SHALL 在文件处理前进行安全扫描，检测恶意内容（宏病毒、嵌入脚本、异常大小）。

#### Scenario: 检测到恶意宏
- **WHEN** Word 文件包含 VBA 宏
- **THEN** 系统 SHALL 剥离宏后继续转换，并在结果中标注 "已移除宏内容"

#### Scenario: 文件炸弹检测
- **WHEN** 压缩文件解压后大小超过原始大小 100 倍
- **THEN** 系统 SHALL 拒绝处理并返回安全警告
