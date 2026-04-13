## 1. 数据模型

- [x] 1.1 在 `src_deepagent/capabilities/skill_creator.py` 中定义 `SkillCreateRequest` Pydantic 模型，包含 `name`（正则校验 `^[a-z][a-z0-9-]*$`）、`description`、`script_name`（默认 `main.py`）、`script_content`（可选）、`doc_content`（可选）、`overwrite`（默认 `False`）字段

## 2. 核心实现

- [x] 2.1 在 `src_deepagent/capabilities/skill_creator.py` 中实现 `_build_skill_md()` 函数，生成符合 SKILL.md frontmatter 规范的文档内容
- [x] 2.2 在 `src_deepagent/capabilities/skill_creator.py` 中实现 `_generate_template_script()` 函数，生成带 argparse 的 Python 模板脚本
- [x] 2.3 在 `src_deepagent/capabilities/skill_creator.py` 中实现 `create_skill(request: SkillCreateRequest) -> dict` 函数，处理目录创建、文件写入、权限设置（0o755）、冲突检测和 registry 注册

## 3. 工具注册

- [x] 3.1 在 `src_deepagent/capabilities/base_tools.py` 中添加 `create_skill` 工具函数（包装 `skill_creator.create_skill`），返回 `WorkerResult` 格式
- [x] 3.2 在 `src_deepagent/capabilities/base_tools.py` 的工具列表中注册 `create_skill`，与 `execute_skill`、`search_skills` 并列

## 4. Agent 工具分配

- [x] 4.1 在 `src_deepagent/agents/factory.py` 中为 Researcher Agent 的工具列表添加 `create_skill`
- [x] 4.2 在 `src_deepagent/agents/factory.py` 中为 Writer Agent 的工具列表添加 `create_skill`

## 5. REST API

- [x] 5.1 在 `src_deepagent/gateway/rest_api.py` 中新增 `POST /skills` 端点，接受 `SkillCreateRequest` JSON body，成功返回 HTTP 201，冲突返回 HTTP 409，校验失败由 FastAPI 自动返回 HTTP 422
