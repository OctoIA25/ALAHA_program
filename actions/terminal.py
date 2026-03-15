import asyncio

from actions.apps import RunCommandAction
from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.terminal")


class WaitAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        ms = params.get("ms", 1000)
        try:
            await asyncio.sleep(ms / 1000)
            return self._ok(waited_ms=ms)
        except Exception as e:
            return self._fail(str(e))
