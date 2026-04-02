"""鉴权中间件

JWT 验证（可选），支持通过 header 或 query param 传递 token。
"""

# 标准库
from typing import Optional

# 第三方库
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# 本地模块
from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 可选的 Bearer Token 认证
_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[dict]:
    """验证请求鉴权（可选）

    开发环境下跳过鉴权，生产环境要求有效的 JWT Token。

    Args:
        request: HTTP 请求
        credentials: Bearer Token

    Returns:
        解码后的 token payload，未鉴权时返回 None

    Raises:
        HTTPException: Token 无效（仅生产环境）
    """
    settings = get_settings()

    # 开发环境跳过鉴权
    if not settings.app.is_production:
        return None

    if not credentials:
        raise HTTPException(status_code=401, detail="缺少认证信息")

    try:
        from jose import jwt

        payload = jwt.decode(
            credentials.credentials,
            settings.app.secret_key,
            algorithms=["HS256"],
        )
        return payload
    except Exception as e:
        logger.warning(f"[Auth] Token 验证失败 | error={e}")
        raise HTTPException(status_code=401, detail="Token 无效或已过期") from e
