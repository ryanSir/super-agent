# Design: PydanticAI OTEL → Langfuse

## 核心链路

```
PydanticAI Agent (instrument=True)
    → OTEL SDK (TracerProvider)
        → OTLPSpanExporter
            → Langfuse OTLP endpoint ({host}/api/public/otel)
```

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/monitoring/otel_setup.py` | 新建 | 配置 TracerProvider + OTLPSpanExporter |
| `src/main.py` | 修改 | 在 `create_app()` 中调用 `setup_otel()` |
| `src/orchestrator/orchestrator_agent.py` | 修改 | Agent 添加 `instrument=True` |
| `src/orchestrator/planner.py` | 修改 | Agent 添加 `instrument=True` |

## otel_setup.py 设计

```python
def setup_otel() -> None:
    """初始化 OTEL → Langfuse 导出"""
    # 1. 构造 Langfuse OTLP endpoint
    endpoint = f"{settings.langfuse.langfuse_host}/api/public/otel"

    # 2. Basic Auth: base64(public_key:secret_key)
    credentials = base64.b64encode(
        f"{public_key}:{secret_key}".encode()
    ).decode()

    # 3. 配置 OTLPSpanExporter
    exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        headers={"Authorization": f"Basic {credentials}"},
    )

    # 4. 注册全局 TracerProvider
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

## Agent 修改

`orchestrator_agent.py:59` 和 `planner.py:23` 的 Agent 构造加一个参数：

```python
Agent(
    model=get_model("planning"),
    ...
    instrument=True,   # 新增
)
```

PydanticAI 会自动将 agent run、tool call、LLM generation 作为 OTEL spans 上报。

## Langfuse session/trace 关联

PydanticAI OTEL spans 默认不携带 `session_id`。通过在调用 `agent.run()` 时传入 OTEL context 可以关联到现有 trace，但这属于进阶优化，当前阶段只需验证数据能进 Langfuse 即可。

## 降级策略

`setup_otel()` 内部 try/except，任何初始化失败只打 warning，不影响服务启动。与现有 `langfuse_tracer.py` 的手动 span 互不干扰。
