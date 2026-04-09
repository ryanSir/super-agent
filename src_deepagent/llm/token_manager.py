"""沙箱临时 JWT 签发

为沙箱环境签发短期 JWT Token，避免暴露真实 API Key。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

_ALGORITHM = "HS256"
_DEFAULT_TTL_MINUTES = 10


def issue_sandbox_token(
    sandbox_id: str,
    task_id: str = "",
    ttl_minutes: int = _DEFAULT_TTL_MINUTES,
) -> str:
    """签发沙箱临时 JWT

    Args:
        sandbox_id: 沙箱实例 ID
        task_id: 关联的任务 ID
        ttl_minutes: Token 有效期（分钟）

    Returns:
        JWT Token 字符串
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": f"sandbox:{sandbox_id}",
        "task_id": task_id,
        "scope": "sandbox:llm_access",
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=_ALGORITHM)
    logger.info(
        f"沙箱 Token 签发 | sandbox_id={sandbox_id} task_id={task_id} ttl={ttl_minutes}m"
    )
    return token


def verify_sandbox_token(token: str) -> dict | None:
    """验证沙箱 JWT

    Returns:
        解码后的 claims 字典，验证失败返回 None
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.JWTError as e:
        logger.warning(f"沙箱 Token 验证失败 | error={e}")
        return None
