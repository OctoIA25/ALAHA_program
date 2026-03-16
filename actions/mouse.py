import asyncio
import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.mouse")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class MoveAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        try:
            pyautogui.moveTo(x, y, duration=0.2)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class ClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        button = params.get("button", "left")
        try:
            pyautogui.click(x, y, button=button)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class DoubleClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        try:
            pyautogui.doubleClick(x, y)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class RightClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        try:
            pyautogui.rightClick(x, y)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class DragAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        fx, fy = params.get("from_x", 0), params.get("from_y", 0)
        tx, ty = params.get("to_x", 0), params.get("to_y", 0)
        try:
            pyautogui.moveTo(fx, fy, duration=0.1)
            pyautogui.drag(tx - fx, ty - fy, duration=0.3)
            return self._ok(x=tx, y=ty)
        except Exception as e:
            return self._fail(str(e))


class ScrollAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        clicks = amount if direction == "up" else -amount
        try:
            pyautogui.scroll(clicks, x=x, y=y)
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
