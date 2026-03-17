import asyncio
import subprocess
import sys

import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.navigate")

_IS_LINUX = sys.platform.startswith("linux")


def _has_xdotool() -> bool:
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_USE_XDOTOOL = _IS_LINUX and _has_xdotool()


class NavigateAction(ActionExecutor):
    """Open a URL in the browser using Ctrl+L (focus address bar) + type + Enter.
    Uses xdotool on Linux for reliable URL input. Works on any browser."""

    async def execute(self, params: dict) -> dict:
        url = params.get("url", "").strip()
        if not url:
            return self._fail("No URL provided")

        try:
            if _USE_XDOTOOL:
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+l"], check=True, timeout=5)
                await asyncio.sleep(0.4)
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+a"], check=True, timeout=5)
                await asyncio.sleep(0.15)
                subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", "--delay", "8", "--", url],
                    check=True, timeout=30,
                )
                await asyncio.sleep(0.15)
                subprocess.run(["xdotool", "key", "--clearmodifiers", "Return"], check=True, timeout=5)
            else:
                pyautogui.hotkey("ctrl", "l")
                await asyncio.sleep(0.4)
                pyautogui.hotkey("ctrl", "a")
                await asyncio.sleep(0.15)
                pyautogui.typewrite(url, interval=0.04)
                await asyncio.sleep(0.15)
                pyautogui.press("enter")

            log.info(f"Navigated to: {url}")
            return self._ok(url=url)
        except Exception as e:
            return self._fail(str(e))
