import asyncio
import json
import sys
import time
from typing import Optional

from core.logger import get_logger
from core.connection import ConnectionServer
from llm.client import LLMClient
from llm.parser import parse_actions, parse_single_action
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
from actions.navigate import NavigateAction

log = get_logger("orchestrator")

SCREENSHOT_SETTLE_MS = 500
MAX_VISION_STEPS = 25

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
    "navigate": NavigateAction(),
    "focus_window": FocusWindowAction(),
    "close_window": CloseWindowAction(),
    "maximize_window": MaximizeWindowAction(),
}

_VISION_SYSTEM_PROMPT_COMMON = """You are ALAHA, an advanced, highly autonomous AI agent that controls a computer.
You have FULL visual access to the screen. Your goal is to complete high-level user requests seamlessly.

Each turn you receive a screenshot and must:
1. THINK: Analyze the screen carefully. What changed? Where are we in the plan? What is the exact next step?
2. ACT: Choose EXACTLY ONE action to execute.

RESPONSE FORMAT (JSON ONLY):
{
  "thinking": "I see the desktop. I need to send a WhatsApp message. I will open Chrome first.",
  "action": {"type": "action_type", ...params}
}

To signal task completion:
{"done": true, "message": "I have successfully sent the message to your fiancee."}

AVAILABLE ACTIONS:
- {"type": "navigate", "url": "https://web.whatsapp.com"}  ← BEST WAY to open any website. Uses Ctrl+L.
- {"type": "open_app", "app": "chrome"} ← Use this to open browsers or basic apps
- {"type": "click", "x": 100, "y": 200}
- {"type": "type", "text": "hello"}
- {"type": "key", "key": "enter"}
- {"type": "wait", "ms": 2000}
- {"type": "hotkey", "keys": ["ctrl", "c"]}
- {"type": "move", "x": 100, "y": 200}
- {"type": "double_click", "x": 100, "y": 200}
- {"type": "right_click", "x": 100, "y": 200}
- {"type": "drag", "from_x": 0, "from_y": 0, "to_x": 100, "to_y": 100}
- {"type": "scroll", "x": 100, "y": 200, "direction": "down", "amount": 3}
- {"type": "run_command", "command": "dir"}
- {"type": "focus_window", "title": "Chrome"}
- {"type": "close_window", "title": "Notepad"}

CRITICAL PLAYBOOKS & HEURISTICS (Follow these to succeed):

1. WEB BROWSING & WHATSAPP:
   - If asked to do something on the web or WhatsApp, immediately use `open_app` with "chrome" or "edge".
   - Once the browser is open, DO NOT click the address bar. Immediately use the `navigate` action with the exact URL (e.g., "https://web.whatsapp.com" or "https://google.com").
   - After navigating, ALWAYS use `wait` (ms: 3000 to 5000) to let the page load before trying to click anything.
   - For WhatsApp: Once loaded, find the "Search or start new chat" box on the left, click it, use `type` for the contact name, use `wait` (ms: 1000), use `key` "enter". Then type the message and press enter.

2. AVOIDING FAILURE & GETTING UNSTUCK:
   - Pixel Precision: Use the EXACT pixel coordinates you see in the screenshot. They match the real screen 1:1.
   - Wait for UI: UIs take time to render. If you just clicked a button or opened an app, your next action should usually be a `wait` (ms: 1000-3000).
   - Recovery: If the screenshot hasn't changed after your last action, your click probably missed or the app is slow. DO NOT repeat the exact same click. Try clicking a different part of the button, or use a keyboard shortcut (like Tab or Enter) instead.

3. PROACTIVITY:
   - Break down vague requests like "message my fiancee" into steps: Open Chrome -> Navigate to WhatsApp -> Wait -> Click Search -> Type name -> Enter -> Type message -> Enter.
   - Do not ask the user for help unless absolutely stuck. Assume you have the authority to complete the task.

RULES:
- Return ONLY valid JSON.
- Always explain your logical step in "thinking".
"""

_SYSTEM_PROMPT_COMMON = """You are ALAHA, an AI agent that controls a computer.
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
- key: {key} - keys: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, f1-f12, win, super, etc.
- hotkey: {keys[]} - example: ["ctrl", "c"] for copy, ["alt", "f4"] to close window
- key_down: {key}
- key_up: {key}
- open_app: {app} - tries to open app directly, may not work for all apps
- run_command: {command}
- focus_window: {title}
- close_window: {title}
- maximize_window: {title}
"""

_VISION_SYSTEM_PROMPT_WINDOWS = _VISION_SYSTEM_PROMPT_COMMON + """WINDOWS TIPS:
- To open an app: press key "win", wait 500ms, type the app name, wait 1000ms, press "enter" — this is the most reliable method
- To bring a window to front: use focus_window with the window title
- For text input fields: click on the field first, then use type
- Start Menu search is always visible after pressing the win key
"""

_VISION_SYSTEM_PROMPT_LINUX = _VISION_SYSTEM_PROMPT_COMMON + """LINUX TIPS:
- To open an app: use run_command with the binary name followed by & (e.g. "google-chrome &")
- To open a terminal: hotkey ["ctrl", "alt", "t"]
- Use focus_window to bring windows to front (requires xdotool or wmctrl)
- Use run_command for any shell operation
"""

_SYSTEM_PROMPT_WINDOWS = _SYSTEM_PROMPT_COMMON + """IMPORTANT TIPS FOR WINDOWS:
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

_SYSTEM_PROMPT_LINUX = _SYSTEM_PROMPT_COMMON + """IMPORTANT TIPS FOR LINUX:
1. To open ANY app reliably, use run_command with the app's binary name, e.g.:
   - {"type": "run_command", "command": "google-chrome &"}
   - {"type": "run_command", "command": "gedit &"}
   - open_app also works for common apps.

2. To bring a window to front, use focus_window with the window title (requires xdotool or wmctrl).

3. Use hotkey ["super"] or ["ctrl", "alt", "t"] to open a terminal.

4. Use run_command for any shell operation (create files, move/rename, etc.).

Respond ONLY with a JSON array of action objects. Example to open a terminal and run a command:
```json
[
  {"type": "hotkey", "keys": ["ctrl", "alt", "t"]},
  {"type": "wait", "ms": 1000},
  {"type": "type", "text": "ls -la"},
  {"type": "key", "key": "enter"}
]
```
"""

SYSTEM_PROMPT = _SYSTEM_PROMPT_LINUX if sys.platform.startswith("linux") else _SYSTEM_PROMPT_WINDOWS
VISION_SYSTEM_PROMPT = _VISION_SYSTEM_PROMPT_LINUX if sys.platform.startswith("linux") else _VISION_SYSTEM_PROMPT_WINDOWS


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
        log.info(f"Vision loop started: {instruction[:80]}")
        action_history: list[dict] = []
        stuck_count = 0
        consecutive_errors = 0
        last_action_key: Optional[str] = None

        try:
            for step in range(MAX_VISION_STEPS):
                screenshot = capture_screenshot()
                if not screenshot:
                    await self._send_error(session_id, step, "Failed to capture screenshot")
                    return

                messages = self._build_vision_messages(instruction, action_history, step, stuck_count, consecutive_errors)
                llm_response = await self.llm.chat_with_vision(messages, screenshot)
                result = parse_single_action(llm_response)

                if result is None:
                    await self._send_error(session_id, step, "LLM returned an invalid response")
                    return

                if result.get("done"):
                    done_message = result.get("message", "")
                    log.info(f"Task complete at step {step + 1}: {done_message}")
                    await self.connection.send({
                        "type": "action_complete",
                        "session_id": session_id,
                        "success": True,
                        "total_actions": step,
                        "message": done_message,
                    })
                    return

                thinking = result.pop("__thinking__", "")
                if thinking:
                    log.info(f"[step {step + 1}] thinking: {thinking[:120]}")
                    await self.connection.send({
                        "type": "agent_thinking",
                        "session_id": session_id,
                        "step": step + 1,
                        "thinking": thinking,
                    })

                action_type = result.get("type", "unknown")
                executor = ACTION_MAP.get(action_type)

                if not executor:
                    log.warning(f"Unknown action type at step {step}: {action_type}")
                    action_history.append({"action": result, "success": False, "error": f"Unknown action: {action_type}"})
                    consecutive_errors += 1
                    continue

                current_action_key = json.dumps(result, sort_keys=True)
                if current_action_key == last_action_key:
                    stuck_count += 1
                    log.warning(f"Same action repeated ({stuck_count}x): {action_type}")
                    if stuck_count >= 5:
                        await self._send_error(session_id, step, "Bot stuck: same action repeated 5 times without progress")
                        return
                else:
                    stuck_count = 0
                    last_action_key = current_action_key

                log.info(f"Vision step [{step + 1}/{MAX_VISION_STEPS}]: {action_type}")

                try:
                    exec_result = await executor.execute(result)
                    success = exec_result.get("success", False)
                    error_msg = exec_result.get("message", "") if not success else ""
                    action_history.append({"action": result, "success": success, "error": error_msg, "thinking": thinking})
                    if not success:
                        consecutive_errors += 1
                    else:
                        consecutive_errors = 0
                except Exception as e:
                    action_history.append({"action": result, "success": False, "error": str(e), "thinking": thinking})
                    consecutive_errors += 1

                await asyncio.sleep(SCREENSHOT_SETTLE_MS / 1000)

                hl_x = exec_result.get("x") if exec_result.get("success") else None
                hl_y = exec_result.get("y") if exec_result.get("success") else None
                post_screenshot = capture_screenshot(hl_x, hl_y)
                if post_screenshot:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": step,
                        "screenshot": post_screenshot,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })

            await self._send_error(
                session_id,
                MAX_VISION_STEPS - 1,
                f"Max steps ({MAX_VISION_STEPS}) reached without completing the task",
            )

        except Exception as e:
            log.error(f"Vision loop error: {e}")
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

    def _build_vision_messages(self, instruction: str, action_history: list[dict], step: int, stuck_count: int = 0, consecutive_errors: int = 0) -> list[dict]:
        history_text = ""
        if action_history:
            lines = []
            for i, h in enumerate(action_history[-10:]):
                action_str = json.dumps(h["action"], ensure_ascii=False)
                status = "OK" if h["success"] else f"FAILED: {h.get('error', '')}"
                thinking_hint = f" | thought: {h['thinking'][:60]}" if h.get("thinking") else ""
                lines.append(f"  {i + 1}. {action_str} -> {status}{thinking_hint}")
            history_text = "\nActions executed so far:\n" + "\n".join(lines)

        warnings = []
        if stuck_count >= 2:
            warnings.append(
                f"⚠️ STUCK WARNING: You repeated the exact same action {stuck_count} times with no progress. "
                "Look at the screenshot carefully. Your click might have missed or the app is not responding. "
                "CHOOSE A DIFFERENT APPROACH (e.g. use keyboard navigation, or click a different area)."
            )
        if consecutive_errors > 0:
            warnings.append(
                f"⚠️ ERROR WARNING: The last {consecutive_errors} actions FAILED. Read the error messages in the history. "
                "Correct your parameters or try a different action type."
            )

        warning_text = "\n\n" + "\n".join(warnings) if warnings else ""

        user_text = (
            f"Task: {instruction}\n"
            f"Current step: {step + 1}/{MAX_VISION_STEPS}"
            f"{history_text}"
            f"{warning_text}\n\n"
            'Look at the screenshot. Think carefully about what you see, then return your response as:\n'
            '{"thinking": "what I see and what I will do", "action": {...}}\n'
            'Or {"done": true, "message": "..."} if the task is complete.'
        )
        return [
            {"role": "system", "content": _VISION_SYSTEM_PROMPT_COMMON},
            {"role": "user", "content": user_text},
        ]

    async def _send_error(self, session_id: str, action_index: int, message: str) -> None:
        await self.connection.send({
            "type": "error",
            "session_id": session_id,
            "action_index": action_index,
            "message": message,
        })
