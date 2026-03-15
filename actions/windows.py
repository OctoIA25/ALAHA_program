import pygetwindow as gw

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.windows")


class FocusWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return self._fail(f"Window not found: {title}")
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            log.info(f"Focused window: {title}")
            return self._ok(title=win.title)
        except Exception as e:
            return self._fail(str(e))


class CloseWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return self._fail(f"Window not found: {title}")
            windows[0].close()
            log.info(f"Closed window: {title}")
            return self._ok()
        except Exception as e:
            return self._fail(str(e))


class MaximizeWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return self._fail(f"Window not found: {title}")
            windows[0].maximize()
            log.info(f"Maximized window: {title}")
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
