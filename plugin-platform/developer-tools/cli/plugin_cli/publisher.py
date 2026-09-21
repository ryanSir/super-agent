from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class PublishResult:
    plugin_id: str
    version: str
    checksum: str
    status: str


class PublishError(RuntimeError):
    pass


def publish_package(
    registry_url: str,
    package_path: Path,
    *,
    timeout_seconds: float = 10.0,
) -> PublishResult:
    if not package_path.exists():
        raise PublishError(f"Package not found: {package_path}")

    try:
        with package_path.open("rb") as package_file:
            response = httpx.post(
                f"{registry_url.rstrip('/')}/api/registry/packages",
                files={"package": (package_path.name, package_file, "application/zip")},
                timeout=timeout_seconds,
            )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise PublishError("Registry publish timed out; retry is safe") from exc
    except httpx.HTTPError as exc:
        raise PublishError(f"Registry publish failed: {exc}") from exc

    payload = response.json()
    return PublishResult(
        plugin_id=payload["plugin_id"],
        version=payload["version"],
        checksum=payload["checksum"],
        status=payload.get("status", "published"),
    )
