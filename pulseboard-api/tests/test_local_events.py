import asyncio
import json

from app import events
from app.core.config import settings


def test_in_memory_events_deliver_to_subscribers(monkeypatch):
    async def run():
        monkeypatch.setattr(settings, "redis_url", "")
        queue = events.subscribe("tenant-test")
        try:
            await events.publish("tenant-test", {"type": "task.created", "task_id": 7})
            assert json.loads(await asyncio.wait_for(queue.get(), timeout=1)) == {
                "type": "task.created", "task_id": 7
            }
        finally:
            events.unsubscribe("tenant-test", queue)

    asyncio.run(run())
