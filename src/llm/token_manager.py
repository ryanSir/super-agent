"""沙箱临时 Token 签发

为 E2B 沙箱签发受限 JWT Token，实现密钥零信任设计。
沙箱内的 Pi Agent 使用临时 Token 访问 LiteLLM 代理，
绝对禁止泄露真实的根密钥。
"""

# 标准库
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# 第三方库
from jose import jwt

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Token 签名算法
ALGORITHM = "HS256"
# 默认有效期 10 分钟
DEFAULT_TTL_MINUTES = 10


def issue_sandbox_token(
    sandbox_id: str,
    task_id: str,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    extra_claims: Optional[Dict] = None,
) -> str:
    """签发沙箱临时 Token

    Args:
        sandbox_id: 沙箱实例 ID
        task_id: 关联的任务 ID
        ttl_minutes: Token 有效期（分钟）
        extra_claims: 额外的 JWT claims

    Returns:
        JWT Token 字符串
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    payload = {
        "sub": f"sandbox:{sandbox_id}",
        "task_id": task_id,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
        "scope": "sandbox:llm_access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.app.secret_key, algorithm=ALGORITHM)

    logger.info(
        f"[TokenManager] 签发沙箱 Token | "
        f"sandbox_id={sandbox_id} task_id={task_id} ttl_min={ttl_minutes}"
    )
    return token


def verify_sandbox_token(token: str) -> Dict:
    """验证沙箱 Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的 payload

    Raises:
        jose.JWTError: Token 无效或已过期
    """
    settings = get_settings()
    return jwt.decode(token, settings.app.secret_key, algorithms=[ALGORITHM])
