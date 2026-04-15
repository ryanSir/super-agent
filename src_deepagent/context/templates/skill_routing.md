<skill_routing>
你可以通过 list_skills 查看可用技能，每个技能有 execution 模式标识：

**Native 模式（execution: native）**
1. 调用 list_skills() 浏览可用技能
2. 调用 load_skill(name) 加载完整 SKILL.md 指引
3. 按 SKILL.md 指引使用 Base Tool / MCP Tool 直接执行
4. 如需读取技能资源文件，调用 read_skill_resource(name, path)

**Sandbox 模式（execution: sandbox）**
1. 调用 list_skills() 浏览可用技能
2. 可选：调用 load_skill(name) 了解技能用途和参数格式
3. 调用 execute_skill(name, params) 委托沙箱执行脚本
4. 简单脚本也可通过 run_skill_script(name, script, args) 直接执行

注意：
- 对 native 技能调用 execute_skill 会被拒绝，请使用 load_skill 后自行执行
- 对 sandbox 技能，execute_skill 会自动注入脚本文件到沙箱环境
</skill_routing>
