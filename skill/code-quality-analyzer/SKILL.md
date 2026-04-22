---
name: code-quality-analyzer
description: 分析代码质量，包括复杂度、规范性、潜在问题检测，支持Python代码，输出结构化质量报告。
---

# Code Quality Analyzer

分析代码质量，包括复杂度、规范性、潜在问题检测，支持Python代码，输出结构化质量报告。

## 可用脚本

### main.py

```bash
python ${CLAUDE_SKILL_DIR}/scripts/main.py [参数]
```


## 使用说明

### 功能概述

分析 Python 代码质量，检测以下维度：

| 维度 | 检测内容 |
|------|----------|
| **复杂度** | 函数圈复杂度（McCabe）、嵌套深度 |
| **规范性** | 命名规范（snake_case / PascalCase） |
| **可维护性** | 函数长度、参数数量、docstring 覆盖率 |
| **可读性** | 注释率、代码行统计 |
| **结构** | 类方法数量、语法错误 |

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `filepath` | string | 要分析的 `.py` 文件路径 |
| `code` | string | 直接传入代码字符串（与 filepath 二选一） |
| `format` | string | 输出格式：`markdown`（默认）或 `json` |

### 评分规则

- 起始分 **100 分**
- 每个 **错误（error）** 扣 10 分
- 每个 **警告（warning）** 扣 3 分
- 每个 **建议（info）** 扣 0.5 分

| 分数区间 | 等级 |
|----------|------|
| 90~100 | 🟢 优秀 |
| 75~89 | 🟡 良好 |
| 60~74 | 🟠 一般 |
| 0~59 | 🔴 较差 |

### 检测阈值

| 指标 | 警告阈值 | 错误阈值 |
|------|----------|----------|
| 函数行数 | > 40 行 | > 80 行 |
| 圈复杂度 | > 7 | > 12 |
| 嵌套深度 | > 3 层 | > 5 层 |
| 参数数量 | > 5 个 | > 8 个 |
| 注释率 | < 10% | — |
| 类方法数 | > 15 个 | — |

### 调用示例

```python
# 分析文件
params = {"filepath": "/path/to/my_module.py"}

# 分析代码字符串
params = {
    "code": "def foo(x):\n    return x * 2\n",
    "format": "markdown"
}

# 输出 JSON
params = {"filepath": "app.py", "format": "json"}
```

