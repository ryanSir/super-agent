"""OpenTelemetry → Langfuse 集成

将 PydanticAI 原生 OTEL instrumentation 导出到 Langfuse OTLP endpoint。
"""

# 标准库
import base64

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def setup_otel() -> None:
    """初始化 OTEL TracerProvider，导出到 Langfuse

    使用 Langfuse 的 OTLP HTTP endpoint，通过 Basic Auth 鉴权。
    初始化失败只打 warning，不影响服务启动。
    """
    settings = get_settings()

    if not settings.langfuse.is_configured:
        logger.info("[OTEL] Langfuse 未配置，跳过 OTEL 初始化")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        public_key = settings.langfuse.langfuse_public_key
        secret_key = settings.langfuse.langfuse_secret_key
        host = settings.langfuse.langfuse_host.rstrip("/")

        endpoint = f"{host}/api/public/otel/v1/traces"
        credentials = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers={"Authorization": f"Basic {credentials}"},
        )

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        logger.info(f"[OTEL] 初始化完成 | endpoint={endpoint}")

    except Exception as e:
        logger.warning(f"[OTEL] 初始化失败，降级运行 | error={e}")
