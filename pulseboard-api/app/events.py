import json
from redis.asyncio import Redis
from app.core.config import settings
async def publish(tenant_id:str,event:dict):
    try:
        client=Redis.from_url(settings.redis_url,decode_responses=True)
        await client.publish(f"tenant:{tenant_id}:events",json.dumps(event))
        await client.aclose()
    except Exception:
        # Event delivery is best-effort in the demo; durable outbox is recommended for production.
        return
