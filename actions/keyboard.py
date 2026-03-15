import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.keyboard")


class TypeAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        try:
            pyautogui.write(text, interval=0.02)
            return self._ok(text=text)
        except Exception as e:
            return self._fail(str(e))


class KeyAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            pyautogui.press(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))


class HotkeyAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        keys = params.get("keys", [])
        try:
            pyautogui.hotkey(*keys)
            return self._ok(keys=keys)
        except Exception as e:
            return self._fail(str(e))


class KeyDownAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            pyautogui.keyDown(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))


class KeyUpAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            pyautogui.keyUp(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))
