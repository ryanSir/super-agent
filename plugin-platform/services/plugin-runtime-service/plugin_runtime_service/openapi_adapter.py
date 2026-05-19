from typing import Any

import httpx
from pydantic import BaseModel

from plugin_runtime_service.errors import RuntimeErrorResult


class OpenApiInvocation(BaseModel):
    method: str
    url: str
    headers: dict[str, str] = {}
    json_body: dict[str, Any] | None = None
    timeout_seconds: float = 10.0


def invoke_openapi(
    invocation: OpenApiInvocation,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any] | RuntimeErrorResult:
    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        response = http_client.request(
            invocation.method,
            invocation.url,
            headers=invocation.headers,
            json=invocation.json_body,
            timeout=invocation.timeout_seconds,
        )
        response.raise_for_status()
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return {"text": response.text}
    except httpx.TimeoutException:
        return RuntimeErrorResult(
            error_code="openapi_timeout",
            message=f"OpenAPI invocation timed out after {invocation.timeout_seconds}s",
            retryable=True,
        )
    except httpx.HTTPError as exc:
        return RuntimeErrorResult(
            error_code="openapi_http_error",
            message=str(exc),
            retryable=False,
        )
    finally:
        if owns_client:
            http_client.close()
