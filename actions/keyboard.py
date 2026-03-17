import subprocess
import sys

import pyautogui

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.keyboard")

_IS_LINUX = sys.platform.startswith("linux")


def _has_xdotool() -> bool:
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _xdotool_type(text: str) -> None:
    """Use xdotool to type text with full Unicode support (accents, special chars)."""
    subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--delay", "12", "--", text],
        check=True, timeout=30,
    )


def _xdotool_key(key: str) -> None:
    """Use xdotool to press a single key. Translates common pyautogui names to X11."""
    key_map = {
        "enter": "Return", "return": "Return",
        "tab": "Tab", "escape": "Escape", "esc": "Escape",
        "backspace": "BackSpace", "delete": "Delete",
        "up": "Up", "down": "Down", "left": "Left", "right": "Right",
        "home": "Home", "end": "End",
        "pageup": "Prior", "pagedown": "Next",
        "space": "space", "super": "super", "win": "super",
        "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
        "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
        "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
        "capslock": "Caps_Lock", "numlock": "Num_Lock",
        "printscreen": "Print", "scrolllock": "Scroll_Lock",
        "insert": "Insert", "pause": "Pause",
    }
    x11_key = key_map.get(key.lower(), key)
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", x11_key],
        check=True, timeout=10,
    )


def _xdotool_hotkey(keys: list[str]) -> None:
    """Use xdotool to press a key combination like ctrl+shift+t."""
    key_map = {
        "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt", "shift": "shift",
        "super": "super", "win": "super",
        "enter": "Return", "return": "Return",
        "tab": "Tab", "escape": "Escape",
        "backspace": "BackSpace", "delete": "Delete",
        "up": "Up", "down": "Down", "left": "Left", "right": "Right",
        "home": "Home", "end": "End",
        "pageup": "Prior", "pagedown": "Next",
        "space": "space",
        "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
        "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
        "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
    }
    x11_keys = [key_map.get(k.lower(), k) for k in keys]
    combo = "+".join(x11_keys)
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", combo],
        check=True, timeout=10,
    )


_USE_XDOTOOL = _IS_LINUX and _has_xdotool()

if _USE_XDOTOOL:
    log.info("Linux detected: using xdotool for keyboard input (Unicode support)")
else:
    log.info("Using pyautogui for keyboard input")


class TypeAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        try:
            if _USE_XDOTOOL:
                _xdotool_type(text)
            else:
                pyautogui.write(text, interval=0.02)
            return self._ok(text=text)
        except Exception as e:
            return self._fail(str(e))


class KeyAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            if _USE_XDOTOOL:
                _xdotool_key(key)
            else:
                pyautogui.press(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))


class HotkeyAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        keys = params.get("keys", [])
        try:
            if _USE_XDOTOOL:
                _xdotool_hotkey(keys)
            else:
                pyautogui.hotkey(*keys)
            return self._ok(keys=keys)
        except Exception as e:
            return self._fail(str(e))


class KeyDownAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            if _USE_XDOTOOL:
                _xdotool_key(key)
            else:
                pyautogui.keyDown(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))


class KeyUpAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        key = params.get("key", "")
        try:
            if _USE_XDOTOOL:
                pass
            else:
                pyautogui.keyUp(key)
            return self._ok(key=key)
        except Exception as e:
            return self._fail(str(e))
