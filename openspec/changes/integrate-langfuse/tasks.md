## 1. 依赖与配置

- [x] 1.1 统一 `pyproject.toml` 中 langfuse 依赖版本为 `^2.55`，同步更新 `requirements.txt`
- [x] 1.2 在 `.env` 中添加 `LANGFUSE_ENABLED=true` 激活追踪

## 2. 核心追踪模块增强

- [x] 2.1 重构 `src_deepagent/monitoring/langfuse_tracer.py`：引入 `@observe()` 装饰器支持，提供 `traced()` 包装函数（未启用时返回原函数）
- [x] 2.2 在 `langfuse_tracer.py` 中新增 `configure_langfuse()` 函数，使用 `langfuse_context.configure()` 初始化全局上下文
- [x] 2.3 在 `main.py` lifespan 启动阶段调用 `configure_langfuse()`，确保追踪上下文在所有请求前就绪

## 3. 请求入口 Trace 接入

- [x] 3.1 在 `src_deepagent/gateway/rest_api.py` 的 `_execute_plan()` 函数入口创建 Trace，绑定 session_id、trace_id、mode、query 到 metadata
- [x] 3.2 确保 `_execute_plan()` 结束时（正常或异常）Trace 正确关闭并上报

## 4. 推理引擎 Span 接入

- [x] 4.1 在 `src_deepagent/orchestrator/reasoning_engine.py` 的 LLM 分类调用处添加 Span，记录 complexity_level、suggested_mode、score
- [x] 4.2 处理分类超时场景：Span 记录 level="ERROR" 和超时信息

## 5. 工具调用 Span 接入

- [x] 5.1 在 `src_deepagent/capabilities/base_tools.py` 的工具执行入口添加 Span 包装，记录工具名称、输入参数、输出结果
- [x] 5.2 处理工具调用失败/超时场景：Span 记录 level="ERROR" 和错误信息

## 6. LLM Generation 追踪

- [x] 6.1 在 `src_deepagent/llm/config.py` 的 `get_model()` 中集成 Langfuse 追踪，记录模型名称和 Token 用量

## 7. 验证

- [x] 7.1 启动应用，发送测试请求，验证 Langfuse stage 环境能收到完整的 Trace → Span → Generation 链路数据
