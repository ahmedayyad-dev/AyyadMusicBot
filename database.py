# pylint: disable=C0114
from redis import asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

_pool = ConnectionPool.from_url(
    'redis://localhost:6379',
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    health_check_interval=30,
    retry_on_timeout=True,
    max_connections=200,
)

database = aioredis.Redis(connection_pool=_pool)
