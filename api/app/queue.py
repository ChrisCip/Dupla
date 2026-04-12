from __future__ import annotations

import redis
from rq import Queue

from app.config import get_settings


def get_redis_connection() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url)


def get_task_queue() -> Queue:
    settings = get_settings()
    conn = get_redis_connection()
    return Queue(settings.rq_queue_name, connection=conn)
