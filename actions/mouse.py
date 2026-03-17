import subprocess
import sys
import time

import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.mouse")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

_IS_LINUX = sys.platform.startswith("linux")


def _has_xdotool() -> bool:
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_USE_XDOTOOL = _IS_LINUX and _has_xdotool()

if _USE_XDOTOOL:
    log.info("Linux detected: using xdotool for mouse control (precise)")
else:
    log.info("Using pyautogui for mouse control")


# ---------------------------------------------------------------------------
# xdotool mouse primitives (Linux only)
# ---------------------------------------------------------------------------

def _xdotool_move(x: int, y: int) -> None:
    """Move mouse to absolute (x, y) with --sync for precision."""
    subprocess.run(
        ["xdotool", "mousemove", "--sync", str(x), str(y)],
        check=True, timeout=5,
    )


def _xdotool_click(x: int, y: int, button: int = 1) -> None:
    """Move + single click. button: 1=left, 2=middle, 3=right."""
    _xdotool_move(x, y)
    time.sleep(0.03)
    subprocess.run(
        ["xdotool", "click", "--delay", "60", str(button)],
        check=True, timeout=5,
    )


def _xdotool_double_click(x: int, y: int) -> None:
    _xdotool_move(x, y)
    time.sleep(0.03)
    subprocess.run(
        ["xdotool", "click", "--repeat", "2", "--delay", "80", "1"],
        check=True, timeout=5,
    )


def _button_number(name: str) -> int:
    return {"left": 1, "middle": 2, "right": 3}.get(name.lower(), 1)


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

class MoveAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        try:
            if _USE_XDOTOOL:
                _xdotool_move(x, y)
            else:
                pyautogui.moveTo(x, y, duration=0.15)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class ClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        button = params.get("button", "left")
        try:
            if _USE_XDOTOOL:
                _xdotool_click(x, y, _button_number(button))
            else:
                pyautogui.click(x, y, button=button)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class DoubleClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        try:
            if _USE_XDOTOOL:
                _xdotool_double_click(x, y)
            else:
                pyautogui.doubleClick(x, y)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class RightClickAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        try:
            if _USE_XDOTOOL:
                _xdotool_click(x, y, button=3)
            else:
                pyautogui.rightClick(x, y)
            return self._ok(x=x, y=y)
        except Exception as e:
            return self._fail(str(e))


class DragAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        fx, fy = int(params.get("from_x", 0)), int(params.get("from_y", 0))
        tx, ty = int(params.get("to_x", 0)), int(params.get("to_y", 0))
        try:
            if _USE_XDOTOOL:
                _xdotool_move(fx, fy)
                time.sleep(0.05)
                subprocess.run(["xdotool", "mousedown", "1"], check=True, timeout=5)
                time.sleep(0.05)
                _xdotool_move(tx, ty)
                time.sleep(0.05)
                subprocess.run(["xdotool", "mouseup", "1"], check=True, timeout=5)
            else:
                pyautogui.moveTo(fx, fy, duration=0.1)
                pyautogui.drag(tx - fx, ty - fy, duration=0.3)
            return self._ok(x=tx, y=ty)
        except Exception as e:
            return self._fail(str(e))


class ScrollAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        direction = params.get("direction", "down")
        amount = int(params.get("amount", 3))
        try:
            if _USE_XDOTOOL:
                _xdotool_move(x, y)
                btn = 4 if direction == "up" else 5
                for _ in range(amount):
                    subprocess.run(
                        ["xdotool", "click", str(btn)],
                        check=True, timeout=5,
                    )
                    time.sleep(0.04)
            else:
                clicks = amount if direction == "up" else -amount
                pyautogui.scroll(clicks, x=x, y=y)
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
