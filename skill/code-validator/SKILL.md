---
name: code-validator
description: This skill will validate the quality, performance, and security aspects of a code snippet provided by the user.
---

# Code Validator

This skill will validate the quality, performance, and security aspects of a code snippet provided by the user.

## 可用脚本

### validate_code.py

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_code.py [参数]
```

# Skill: Code Validator

## Description
This skill is designed to validate and analyze the quality, performance, and security of a given code snippet. It can be used to:
1. Assess code readability and maintainability.
2. Identify potential security vulnerabilities.
3. Recommend performance optimizations.

### Example Usage
```python
# Example Code Snippet
def example_function():
    pass

# Inputs to validate
results = validate_code({"language": "python", "code_snippet": "def example_function():\n    pass"})
```
Parameters:
- `language` (str): The programming language (e.g., Python, Java, etc.)
- `code_snippet` (str): The raw code snippet to validate.

### Example Result
The skill will return a dictionary with keys such as `quality_score`, `issues_found`, and `recommendations`.
