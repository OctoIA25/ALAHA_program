from abc import ABC, abstractmethod
from typing import Optional

from core.logger import get_logger

log = get_logger("actions.base")


class ActionExecutor(ABC):
    @abstractmethod
    async def execute(self, params: dict) -> dict:
        """Execute the action and return a result dict with at least 'success' key."""
        ...

    def _ok(self, **extra) -> dict:
        return {"success": True, **extra}

    def _fail(self, message: str, **extra) -> dict:
        log.error(f"Action failed: {message}")
        return {"success": False, "message": message, **extra}
