#!/usr/bin/env python3
"""
Code Quality Analyzer
分析Python代码质量，输出结构化报告
"""

import ast
import sys
import os
import re
import json
import textwrap
import subprocess
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple


# ─── 数据结构 ────────────────────────────────────────────────────────────────

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    end_lineno: int
    line_count: int
    arg_count: int
    complexity: int          # 圈复杂度（McCabe）
    max_nesting: int         # 最大嵌套深度
    has_docstring: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    lineno: int
    end_lineno: int
    method_count: int
    has_docstring: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    filepath: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    comment_ratio: float
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    issues: List[Dict]         # {"level": "error/warning/info", "line": n, "msg": "..."}
    score: float               # 0~100
    summary: str


# ─── AST 分析器 ──────────────────────────────────────────────────────────────

class ComplexityVisitor(ast.NodeVisitor):
    """计算函数/方法的圈复杂度"""

    def __init__(self):
        self.complexity = 1   # 基础复杂度为 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        if node.ifs:
            self.complexity += len(node.ifs)
        self.generic_visit(node)


def calc_complexity(func_node: ast.FunctionDef) -> int:
    v = ComplexityVisitor()
    v.visit(func_node)
    return v.complexity


class NestingVisitor(ast.NodeVisitor):
    """计算最大嵌套深度"""

    def __init__(self):
        self.depth = 0
        self.max_depth = 0

    def _visit_block(self, node):
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    visit_If = _visit_block
    visit_For = _visit_block
    visit_While = _visit_block
    visit_With = _visit_block
    visit_Try = _visit_block


def calc_nesting(func_node: ast.FunctionDef) -> int:
    v = NestingVisitor()
    v.visit(func_node)
    return v.max_depth


def has_docstring(node) -> bool:
    return (
        isinstance(node.body, list)
        and len(node.body) > 0
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    )


# ─── 行级统计 ─────────────────────────────────────────────────────────────────

def count_lines(source: str) -> Tuple[int, int, int, int]:
    """返回 (total, code, comment, blank)"""
    lines = source.splitlines()
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith('#'))
    code = total - blank - comment
    return total, code, comment, blank


# ─── 命名规范检查 ─────────────────────────────────────────────────────────────

SNAKE_CASE = re.compile(r'^[a-z_][a-z0-9_]*$')
PASCAL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
SCREAMING_SNAKE = re.compile(r'^[A-Z_][A-Z0-9_]*$')


def check_naming(name: str, kind: str) -> Optional[str]:
    if kind == 'function' and not SNAKE_CASE.match(name):
        return f"函数名 '{name}' 不符合 snake_case 规范"
    if kind == 'class' and not PASCAL_CASE.match(name):
        return f"类名 '{name}' 不符合 PascalCase 规范"
    if kind == 'variable':
        if not SNAKE_CASE.match(name) and not SCREAMING_SNAKE.match(name):
            return f"变量名 '{name}' 不符合命名规范"
    return None


# ─── 主分析逻辑 ───────────────────────────────────────────────────────────────

# 阈值配置
THRESHOLDS = {
    "func_lines_warn": 40,
    "func_lines_error": 80,
    "complexity_warn": 7,
    "complexity_error": 12,
    "nesting_warn": 3,
    "nesting_error": 5,
    "args_warn": 5,
    "args_error": 8,
    "comment_ratio_warn": 0.10,
    "class_methods_warn": 15,
}


def analyze_source(source: str, filepath: str = "<string>") -> QualityReport:
    total, code, comment, blank = count_lines(source)
    comment_ratio = comment / total if total else 0.0

    issues: List[Dict] = []

    def add_issue(level: str, line: int, msg: str):
        issues.append({"level": level, "line": line, "msg": msg})

    # 注释率过低
    if comment_ratio < THRESHOLDS["comment_ratio_warn"] and code > 50:
        add_issue("warning", 0, f"注释率 {comment_ratio:.1%} 偏低（建议 ≥10%）")

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        add_issue("error", e.lineno or 0, f"语法错误: {e.msg}")
        return QualityReport(
            filepath=filepath, total_lines=total, code_lines=code,
            comment_lines=comment, blank_lines=blank,
            comment_ratio=comment_ratio, functions=[], classes=[],
            issues=issues, score=0.0,
            summary="❌ 代码存在语法错误，无法完成完整分析。"
        )

    functions: List[FunctionInfo] = []
    classes: List[ClassInfo] = []

    for node in ast.walk(tree):
        # ── 函数分析 ─────────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, 'end_lineno', node.lineno)
            lc = end - node.lineno + 1
            complexity = calc_complexity(node)
            nesting = calc_nesting(node)
            argc = len(node.args.args) + len(node.args.posonlyargs)
            doc = has_docstring(node)
            func_issues = []

            nm_issue = check_naming(node.name, 'function')
            if nm_issue:
                add_issue("warning", node.lineno, nm_issue)

            if lc > THRESHOLDS["func_lines_error"]:
                msg = f"函数 '{node.name}' 过长（{lc} 行，建议 <{THRESHOLDS['func_lines_error']} 行）"
                func_issues.append(msg)
                add_issue("error", node.lineno, msg)
            elif lc > THRESHOLDS["func_lines_warn"]:
                msg = f"函数 '{node.name}' 较长（{lc} 行，建议 <{THRESHOLDS['func_lines_warn']} 行）"
                func_issues.append(msg)
                add_issue("warning", node.lineno, msg)

            if complexity > THRESHOLDS["complexity_error"]:
                msg = f"函数 '{node.name}' 圈复杂度过高（{complexity}，建议 ≤{THRESHOLDS['complexity_error']}）"
                func_issues.append(msg)
                add_issue("error", node.lineno, msg)
            elif complexity > THRESHOLDS["complexity_warn"]:
                msg = f"函数 '{node.name}' 圈复杂度较高（{complexity}，建议 ≤{THRESHOLDS['complexity_warn']}）"
                func_issues.append(msg)
                add_issue("warning", node.lineno, msg)

            if nesting > THRESHOLDS["nesting_error"]:
                msg = f"函数 '{node.name}' 嵌套深度过深（{nesting} 层，建议 ≤{THRESHOLDS['nesting_error']} 层）"
                func_issues.append(msg)
                add_issue("error", node.lineno, msg)
            elif nesting > THRESHOLDS["nesting_warn"]:
                msg = f"函数 '{node.name}' 嵌套深度较深（{nesting} 层，建议 ≤{THRESHOLDS['nesting_warn']} 层）"
                func_issues.append(msg)
                add_issue("warning", node.lineno, msg)

            if argc > THRESHOLDS["args_error"]:
                msg = f"函数 '{node.name}' 参数过多（{argc} 个，建议 ≤{THRESHOLDS['args_error']} 个）"
                func_issues.append(msg)
                add_issue("error", node.lineno, msg)
            elif argc > THRESHOLDS["args_warn"]:
                msg = f"函数 '{node.name}' 参数较多（{argc} 个，建议 ≤{THRESHOLDS['args_warn']} 个）"
                func_issues.append(msg)
                add_issue("warning", node.lineno, msg)

            if not doc:
                add_issue("info", node.lineno, f"函数 '{node.name}' 缺少 docstring")

            functions.append(FunctionInfo(
                name=node.name, lineno=node.lineno, end_lineno=end,
                line_count=lc, arg_count=argc, complexity=complexity,
                max_nesting=nesting, has_docstring=doc, issues=func_issues
            ))

        # ── 类分析 ───────────────────────────────────
        elif isinstance(node, ast.ClassDef):
            end = getattr(node, 'end_lineno', node.lineno)
            methods = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            doc = has_docstring(node)
            cls_issues = []

            nm_issue = check_naming(node.name, 'class')
            if nm_issue:
                add_issue("warning", node.lineno, nm_issue)

            if len(methods) > THRESHOLDS["class_methods_warn"]:
                msg = f"类 '{node.name}' 方法过多（{len(methods)} 个，建议拆分）"
                cls_issues.append(msg)
                add_issue("warning", node.lineno, msg)

            if not doc:
                add_issue("info", node.lineno, f"类 '{node.name}' 缺少 docstring")

            classes.append(ClassInfo(
                name=node.name, lineno=node.lineno, end_lineno=end,
                method_count=len(methods), has_docstring=doc, issues=cls_issues
            ))

    # ── 评分 ─────────────────────────────────────────
    deductions = 0
    for issue in issues:
        if issue["level"] == "error":
            deductions += 10
        elif issue["level"] == "warning":
            deductions += 3
        elif issue["level"] == "info":
            deductions += 0.5

    score = max(0.0, min(100.0, 100.0 - deductions))

    # ── 摘要 ─────────────────────────────────────────
    errors = sum(1 for i in issues if i["level"] == "error")
    warnings = sum(1 for i in issues if i["level"] == "warning")
    infos = sum(1 for i in issues if i["level"] == "info")

    if score >= 90:
        grade = "🟢 优秀"
    elif score >= 75:
        grade = "🟡 良好"
    elif score >= 60:
        grade = "🟠 一般"
    else:
        grade = "🔴 较差"

    summary = (
        f"{grade}（{score:.1f}/100）｜"
        f"错误 {errors} · 警告 {warnings} · 建议 {infos}｜"
        f"函数 {len(functions)} · 类 {len(classes)} · "
        f"总行数 {total}（注释率 {comment_ratio:.1%}）"
    )

    return QualityReport(
        filepath=filepath, total_lines=total, code_lines=code,
        comment_lines=comment, blank_lines=blank,
        comment_ratio=comment_ratio, functions=functions, classes=classes,
        issues=issues, score=score, summary=summary
    )


# ─── 输出格式化 ───────────────────────────────────────────────────────────────

def render_markdown(report: QualityReport) -> str:
    lines = []
    lines.append(f"# 代码质量分析报告\n")
    lines.append(f"**文件**: `{report.filepath}`\n")
    lines.append(f"**综合评分**: {report.summary}\n")

    # 统计摘要
    lines.append("## 📊 代码统计\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总行数 | {report.total_lines} |")
    lines.append(f"| 代码行数 | {report.code_lines} |")
    lines.append(f"| 注释行数 | {report.comment_lines} |")
    lines.append(f"| 空白行数 | {report.blank_lines} |")
    lines.append(f"| 注释率 | {report.comment_ratio:.1%} |")
    lines.append(f"| 函数数量 | {len(report.functions)} |")
    lines.append(f"| 类数量 | {len(report.classes)} |")
    lines.append("")

    # 问题列表
    errors = [i for i in report.issues if i["level"] == "error"]
    warnings = [i for i in report.issues if i["level"] == "warning"]
    infos = [i for i in report.issues if i["level"] == "info"]

    if errors:
        lines.append("## 🔴 错误（需要修复）\n")
        for i in errors:
            loc = f"第 {i['line']} 行" if i['line'] else "全局"
            lines.append(f"- **[{loc}]** {i['msg']}")
        lines.append("")

    if warnings:
        lines.append("## 🟡 警告（建议改进）\n")
        for i in warnings:
            loc = f"第 {i['line']} 行" if i['line'] else "全局"
            lines.append(f"- **[{loc}]** {i['msg']}")
        lines.append("")

    if infos:
        lines.append("## 🔵 建议（可选优化）\n")
        for i in infos:
            loc = f"第 {i['line']} 行" if i['line'] else "全局"
            lines.append(f"- [{loc}] {i['msg']}")
        lines.append("")

    # 函数详情
    if report.functions:
        lines.append("## 🔧 函数质量详情\n")
        lines.append("| 函数名 | 行号 | 行数 | 圈复杂度 | 最大嵌套 | 参数数 | Docstring |")
        lines.append("|--------|------|------|----------|----------|--------|-----------|")
        for f in sorted(report.functions, key=lambda x: x.complexity, reverse=True):
            doc_icon = "✅" if f.has_docstring else "❌"
            cplx_icon = "🔴" if f.complexity > THRESHOLDS["complexity_error"] else \
                        "🟡" if f.complexity > THRESHOLDS["complexity_warn"] else "🟢"
            lines.append(
                f"| `{f.name}` | {f.lineno} | {f.line_count} | "
                f"{cplx_icon} {f.complexity} | {f.max_nesting} | {f.arg_count} | {doc_icon} |"
            )
        lines.append("")

    # 类详情
    if report.classes:
        lines.append("## 🏛️ 类质量详情\n")
        lines.append("| 类名 | 行号 | 方法数 | Docstring |")
        lines.append("|------|------|--------|-----------|")
        for c in report.classes:
            doc_icon = "✅" if c.has_docstring else "❌"
            lines.append(f"| `{c.name}` | {c.lineno} | {c.method_count} | {doc_icon} |")
        lines.append("")

    # 改进建议
    lines.append("## 💡 改进建议\n")
    suggestions = []
    if report.comment_ratio < THRESHOLDS["comment_ratio_warn"] and report.code_lines > 50:
        suggestions.append("增加注释，提升代码可读性")
    high_complexity = [f for f in report.functions if f.complexity > THRESHOLDS["complexity_warn"]]
    if high_complexity:
        names = ', '.join(f'`{f.name}`' for f in high_complexity[:3])
        suggestions.append(f"重构高复杂度函数（{names}），考虑拆分为更小的函数")
    no_doc_funcs = [f for f in report.functions if not f.has_docstring]
    if len(no_doc_funcs) > 0:
        suggestions.append(f"为 {len(no_doc_funcs)} 个函数补充 docstring 文档")
    deep_nesting = [f for f in report.functions if f.max_nesting > THRESHOLDS["nesting_warn"]]
    if deep_nesting:
        names = ', '.join(f'`{f.name}`' for f in deep_nesting[:3])
        suggestions.append(f"减少嵌套深度（{names}），考虑提前返回（early return）模式")

    if suggestions:
        for s in suggestions:
            lines.append(f"1. {s}")
    else:
        lines.append("代码质量良好，继续保持！")
    lines.append("")

    return "\n".join(lines)


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    params_str = os.environ.get("SKILL_PARAMS", "{}")
    try:
        params = json.loads(params_str)
    except json.JSONDecodeError:
        params = {}

    filepath = params.get("filepath")
    code = params.get("code")
    output_format = params.get("format", "markdown")   # markdown | json

    if filepath:
        p = Path(filepath)
        if not p.exists():
            print(f"❌ 文件不存在: {filepath}")
            sys.exit(1)
        source = p.read_text(encoding="utf-8")
        label = str(p)
    elif code:
        source = textwrap.dedent(code)
        label = "<inline code>"
    else:
        print("❌ 请提供 'filepath'（文件路径）或 'code'（代码字符串）参数")
        sys.exit(1)

    report = analyze_source(source, label)

    if output_format == "json":
        # 将 dataclass 序列化，但 List[FunctionInfo] 需手动处理
        data = {
            "filepath": report.filepath,
            "score": report.score,
            "summary": report.summary,
            "stats": {
                "total_lines": report.total_lines,
                "code_lines": report.code_lines,
                "comment_lines": report.comment_lines,
                "blank_lines": report.blank_lines,
                "comment_ratio": report.comment_ratio,
            },
            "functions": [asdict(f) for f in report.functions],
            "classes": [asdict(c) for c in report.classes],
            "issues": report.issues,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))


if __name__ == "__main__":
    main()
