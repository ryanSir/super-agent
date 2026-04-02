# Tasks: PydanticAI OTEL → Langfuse

## [x] Task 1: 新建 `src/monitoring/otel_setup.py`

新建文件，实现 `setup_otel()` 函数：
- 从 `settings.langfuse` 读取 `langfuse_host`、`langfuse_public_key`、`langfuse_secret_key`
- 若 `is_configured` 为 False，直接 return
- 构造 OTLP endpoint：`{langfuse_host}/api/public/otel/v1/traces`
- 构造 Basic Auth header：`base64(public_key:secret_key)`
- 创建 `OTLPSpanExporter`（来自 `opentelemetry.exporter.otlp.proto.http.trace_exporter`）
- 创建 `TracerProvider`，添加 `BatchSpanProcessor(exporter)`
- 调用 `opentelemetry.trace.set_tracer_provider(provider)`
- 整体 try/except，失败只 `logger.warning`

## [x] Task 2: 修改 `src/main.py` — 调用 `setup_otel()`

在 `create_app()` 函数中，`setup_litellm()` 调用之后，添加：
```python
from src.monitoring.otel_setup import setup_otel
setup_otel()
```

## [x] Task 3: 修改 `src/orchestrator/orchestrator_agent.py` — orchestrator_agent 添加 instrument

在 `orchestrator_agent.py:59` 的 `Agent(...)` 构造中添加 `instrument=True` 参数。

## [x] Task 4: 修改 `src/orchestrator/planner.py` — planner_agent 添加 instrument

在 `planner.py:23` 的 `Agent(...)` 构造中添加 `instrument=True` 参数。
