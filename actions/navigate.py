import asyncio
import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.navigate")


class NavigateAction(ActionExecutor):
    """Open a URL in the browser using Ctrl+L (focus address bar) + type + Enter.
    Works regardless of where the address bar is on screen."""

    async def execute(self, params: dict) -> dict:
        url = params.get("url", "").strip()
        if not url:
            return self._fail("No URL provided")

        try:
            pyautogui.hotkey("ctrl", "l")
            await asyncio.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            await asyncio.sleep(0.1)
            pyautogui.typewrite(url, interval=0.04)
            await asyncio.sleep(0.1)
            pyautogui.press("enter")
            log.info(f"Navigated to: {url}")
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
