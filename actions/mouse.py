import asyncio
import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger
from screenshot.capture import TARGET_SIZE

log = get_logger("actions.mouse")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

_SCREEN_SIZE: tuple[int, int] | None = None


def _get_screen_size() -> tuple[int, int]:
    global _SCREEN_SIZE
    if _SCREEN_SIZE is None:
        w, h = pyautogui.size()
        _SCREEN_SIZE = (w, h)
        log.info(f"Screen resolution: {w}x{h}, screenshot space: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")
    return _SCREEN_SIZE


def _scale(x: int | float, y: int | float) -> tuple[int, int]:
    """Convert coordinates from screenshot space (1280x720) to actual screen resolution."""
    sw, sh = _get_screen_size()
    sx = int(x * sw / TARGET_SIZE[0])
    sy = int(y * sh / TARGET_SIZE[1])
    return sx, sy


class MoveAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        sx, sy = _scale(x, y)
        try:
            pyautogui.moveTo(sx, sy, duration=0.2)
            return self._ok(x=sx, y=sy)
        except Exception as e:
            return self._fail(str(e))


class ClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        button = params.get("button", "left")
        sx, sy = _scale(x, y)
        try:
            pyautogui.click(sx, sy, button=button)
            return self._ok(x=sx, y=sy)
        except Exception as e:
            return self._fail(str(e))


class DoubleClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        sx, sy = _scale(x, y)
        try:
            pyautogui.doubleClick(sx, sy)
            return self._ok(x=sx, y=sy)
        except Exception as e:
            return self._fail(str(e))


class RightClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 0), params.get("y", 0)
        sx, sy = _scale(x, y)
        try:
            pyautogui.rightClick(sx, sy)
            return self._ok(x=sx, y=sy)
        except Exception as e:
            return self._fail(str(e))


class DragAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        fx, fy = params.get("from_x", 0), params.get("from_y", 0)
        tx, ty = params.get("to_x", 0), params.get("to_y", 0)
        sfx, sfy = _scale(fx, fy)
        stx, sty = _scale(tx, ty)
        try:
            pyautogui.moveTo(sfx, sfy, duration=0.1)
            pyautogui.drag(stx - sfx, sty - sfy, duration=0.3)
            return self._ok()
        except Exception as e:
            return self._fail(str(e))


class ScrollAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = params.get("x", 640), params.get("y", 360)
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        clicks = amount if direction == "up" else -amount
        sx, sy = _scale(x, y)
        try:
            pyautogui.scroll(clicks, x=sx, y=sy)
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
