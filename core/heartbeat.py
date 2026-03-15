import asyncio
import json
import time

from core.logger import get_logger

log = get_logger("heartbeat")

HEARTBEAT_INTERVAL = 30  # seconds


async def heartbeat_loop(ws, agent_id: str) -> None:
    while True:
        try:
            payload = json.dumps({
                "type": "heartbeat",
                "agent_id": agent_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            await ws.send(payload)
            log.debug("Heartbeat sent")
        except Exception as e:
            log.warning(f"Heartbeat failed: {e}")
            break
        await asyncio.sleep(HEARTBEAT_INTERVAL)
