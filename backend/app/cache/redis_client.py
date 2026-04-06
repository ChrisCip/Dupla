import json
from typing import Any, Optional, Union

import redis.asyncio as redis

from app.config import get_settings


async def cache_get_json(key: str) -> Optional[Union[dict[str, Any], list[Any]]]:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None
    finally:
        await client.aclose()


async def cache_set_json(key: str, value: Union[dict[str, Any], list[Any]], ttl_seconds: int) -> None:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        return
    finally:
        await client.aclose()
