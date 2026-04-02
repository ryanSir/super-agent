"""FastAPI 全局依赖注入

通过 Depends 工厂提供 Settings、Redis 等共享资源。
支持 Redis 单机模式和集群模式。
"""

# 标准库
from typing import Optional, Union

# 第三方库
import redis.asyncio as aioredis
from redis.asyncio.cluster import RedisCluster
from fastapi import Depends

# 本地模块
from src.config.settings import Settings, get_settings

# Redis 连接（应用生命周期内复用）
_redis_pool: Optional[Union[aioredis.Redis, RedisCluster]] = None


def _create_redis_client(settings: Settings) -> Union[aioredis.Redis, RedisCluster]:
    """根据配置创建 Redis 客户端（单机 or 集群）"""
    if settings.redis.redis_cluster_mode:
        return RedisCluster(
            host=settings.redis.redis_host,
            port=settings.redis.redis_port,
            password=settings.redis.redis_password or None,
            decode_responses=True,
        )
    else:
        return aioredis.from_url(
            settings.redis.url,
            max_connections=settings.redis.redis_max_connections,
            decode_responses=True,
        )


async def get_redis(settings: Settings = Depends(get_settings)):
    """获取 Redis 异步客户端（FastAPI Depends 上下文）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = _create_redis_client(settings)
    return _redis_pool


async def get_redis_client():
    """获取 Redis 异步客户端（非 Depends 上下文，供 streaming/worker 层使用）"""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = _create_redis_client(settings)
    return _redis_pool


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
