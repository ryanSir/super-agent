"""DAG 规划 Prompt

从 planning.md 加载提示词模板，保持代码与提示词分离。
"""

from pathlib import Path

_PROMPT_FILE = Path(__file__).parent / "planning.md"
PLANNING_PROMPT_TEMPLATE = _PROMPT_FILE.read_text(encoding="utf-8")
