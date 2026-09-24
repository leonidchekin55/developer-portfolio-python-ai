import asyncio
import json
from collections import defaultdict

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)

def subscribe(tenant_id:str) -> asyncio.Queue[str]:
    queue:asyncio.Queue[str]=asyncio.Queue(maxsize=100)
    _subscribers[tenant_id].add(queue)
    return queue

def unsubscribe(tenant_id:str,queue:asyncio.Queue[str]) -> None:
    _subscribers[tenant_id].discard(queue)
    if not _subscribers[tenant_id]: _subscribers.pop(tenant_id,None)

async def publish(tenant_id:str,event:dict):
    payload=json.dumps(event)
    if not settings.redis_url:
        for queue in tuple(_subscribers.get(tenant_id,())):
            if queue.full():
                try: queue.get_nowait()
                except asyncio.QueueEmpty: pass
            try: queue.put_nowait(payload)
            except asyncio.QueueFull: pass
        return
    try:
        client=Redis.from_url(settings.redis_url,decode_responses=True)
        await client.publish(f"tenant:{tenant_id}:events",payload)
        await client.aclose()
    except RedisError:
        # Event delivery is best-effort in the demo; durable outbox is recommended for production.
        return
