import asyncio
import time
from typing import Optional

from core.logger import get_logger
from core.connection import ConnectionServer
from llm.client import LLMClient
from llm.parser import parse_actions
from screenshot.capture import capture_screenshot

from actions.base import ActionExecutor
from actions.mouse import (
    MoveAction, ClickAction, DoubleClickAction, RightClickAction, DragAction, ScrollAction,
)
from actions.keyboard import (
    TypeAction, KeyAction, HotkeyAction, KeyDownAction, KeyUpAction,
)
from actions.apps import OpenAppAction, RunCommandAction
from actions.windows import FocusWindowAction, CloseWindowAction, MaximizeWindowAction
from actions.terminal import WaitAction

log = get_logger("orchestrator")

SCREENSHOT_SETTLE_MS = 500

ACTION_MAP: dict[str, ActionExecutor] = {
    "wait": WaitAction(),
    "move": MoveAction(),
    "click": ClickAction(),
    "double_click": DoubleClickAction(),
    "right_click": RightClickAction(),
    "drag": DragAction(),
    "scroll": ScrollAction(),
    "type": TypeAction(),
    "key": KeyAction(),
    "hotkey": HotkeyAction(),
    "key_down": KeyDownAction(),
    "key_up": KeyUpAction(),
    "open_app": OpenAppAction(),
    "run_command": RunCommandAction(),
    "focus_window": FocusWindowAction(),
    "close_window": CloseWindowAction(),
    "maximize_window": MaximizeWindowAction(),
}

SYSTEM_PROMPT = """You are ALAHA, an AI agent that controls a Windows computer.
You receive an instruction from the user and must return a JSON array of actions to execute on the computer.

Available action types:
- wait: {ms}
- move: {x, y}
- click: {x, y, button?}
- double_click: {x, y}
- right_click: {x, y}
- drag: {from_x, from_y, to_x, to_y}
- scroll: {x, y, direction, amount}
- type: {text}
- key: {key} - keys: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, f1-f12, win, etc.
- hotkey: {keys[]} - example: ["ctrl", "c"] for copy, ["alt", "f4"] to close window
- key_down: {key}
- key_up: {key}
- open_app: {app} - tries to open app directly, may not work for all apps
- run_command: {command}
- focus_window: {title}
- close_window: {title}
- maximize_window: {title}

IMPORTANT TIPS FOR WINDOWS:
1. To open ANY app reliably, use the Windows Start Menu search:
   - Press "win" key to open Start Menu
   - Type the app name (e.g., "whatsapp", "chrome", "notepad")
   - Press "enter" to launch it
   This is MORE RELIABLE than open_app for most applications.

2. If an app is already open, use focus_window to bring it to front.

3. For WhatsApp Desktop:
   - Open via Start Menu: key "win", wait, type "whatsapp", wait, key "enter"
   - Search contacts: use Ctrl+F or just start typing in the search box
   - Send message: type the message, then press "enter"

Respond ONLY with a JSON array of action objects. Example to open WhatsApp and send a message:
```json
[
  {"type": "key", "key": "win"},
  {"type": "wait", "ms": 500},
  {"type": "type", "text": "whatsapp"},
  {"type": "wait", "ms": 1000},
  {"type": "key", "key": "enter"},
  {"type": "wait", "ms": 2000},
  {"type": "hotkey", "keys": ["ctrl", "f"]},
  {"type": "wait", "ms": 300},
  {"type": "type", "text": "Gabriel"},
  {"type": "wait", "ms": 500},
  {"type": "key", "key": "enter"},
  {"type": "wait", "ms": 500},
  {"type": "type", "text": "Hello!"},
  {"type": "key", "key": "enter"}
]
```
"""


class Orchestrator:
    def __init__(self, connection: ConnectionServer, llm: LLMClient):
        self.connection = connection
        self.llm = llm
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    async def handle_instruction(self, message: dict) -> None:
        session_id = message.get("session_id", "unknown")
        instruction = message.get("instruction", "")

        if not instruction:
            log.warning("Empty instruction received")
            await self._send_error(session_id, 0, "Empty instruction")
            return

        if not self.llm.is_configured:
            log.error("LLM not configured, cannot process instruction")
            await self._send_error(session_id, 0, "LLM not configured")
            return

        self._busy = True
        log.info(f"Processing instruction: {instruction[:80]}...")

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": instruction},
            ]
            llm_response = await self.llm.chat(messages)
            actions = parse_actions(llm_response)

            if not actions:
                await self._send_error(session_id, 0, "LLM returned no valid actions")
                return

            await self._execute_actions(session_id, actions)

        except Exception as e:
            log.error(f"Orchestrator error: {e}")
            await self._send_error(session_id, 0, str(e))
        finally:
            self._busy = False

    async def handle_execute_actions(self, message: dict) -> None:
        session_id = message.get("session_id", "unknown")
        actions = message.get("actions", [])

        if not actions:
            await self._send_error(session_id, 0, "No actions provided")
            return

        self._busy = True
        try:
            await self._execute_actions(session_id, actions)
        finally:
            self._busy = False

    async def _execute_actions(self, session_id: str, actions: list[dict]) -> None:
        total = len(actions)
        log.info(f"Executing {total} actions for session {session_id}")

        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            executor = ACTION_MAP.get(action_type)

            if not executor:
                log.warning(f"Unknown action type: {action_type}")
                await self._send_error(session_id, i, f"Unknown action: {action_type}")
                continue

            log.info(f"Action [{i+1}/{total}]: {action_type}")

            try:
                result = await executor.execute(action)

                if not result.get("success"):
                    await self._send_error(session_id, i, result.get("message", "Unknown error"))
                    continue

                await asyncio.sleep(SCREENSHOT_SETTLE_MS / 1000)

                highlight_x = action.get("x")
                highlight_y = action.get("y")
                screenshot = capture_screenshot(highlight_x, highlight_y)

                if screenshot:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": i,
                        "screenshot": screenshot,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })

            except Exception as e:
                log.error(f"Action execution error at index {i}: {e}")
                await self._send_error(session_id, i, str(e))

        await self.connection.send({
            "type": "action_complete",
            "session_id": session_id,
            "success": True,
            "total_actions": total,
        })
        log.info(f"All {total} actions completed for session {session_id}")

    async def _send_error(self, session_id: str, action_index: int, message: str) -> None:
        await self.connection.send({
            "type": "error",
            "session_id": session_id,
            "action_index": action_index,
            "message": message,
        })
