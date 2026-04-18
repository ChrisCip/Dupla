import json
from typing import Any, Optional, Union
from uuid import UUID

import redis.asyncio as redis

from app.config import get_settings


def chat_message_epoch_key(conversation_uuid: UUID) -> str:
    return f"chat:msg_epoch:{conversation_uuid}"


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


async def chat_message_epoch_get(conversation_uuid: UUID) -> int:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await client.get(chat_message_epoch_key(conversation_uuid))
        if raw is None:
            return 0
        return int(raw)
    except Exception:
        return 0
    finally:
        await client.aclose()


async def chat_message_epoch_bump(conversation_uuid: UUID) -> int:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        return int(await client.incr(chat_message_epoch_key(conversation_uuid)))
    except Exception:
        return 0
    finally:
        await client.aclose()
