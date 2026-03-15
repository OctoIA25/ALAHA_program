import subprocess
import sys

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.apps")

WINDOWS_APP_MAP = {
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "wordpad": "write.exe",
}


class OpenAppAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        app = params.get("app", "")
        try:
            executable = WINDOWS_APP_MAP.get(app.lower(), app)
            if sys.platform == "win32":
                subprocess.Popen(
                    ["start", "", executable],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            log.info(f"Opened app: {app} -> {executable}")
            return self._ok(app=app)
        except Exception as e:
            return self._fail(str(e))


class RunCommandAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        command = params.get("command", "")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout[:2000] if result.stdout else ""
            error = result.stderr[:500] if result.stderr else ""
            log.info(f"Command executed: {command[:60]}")
            return self._ok(
                output=output,
                error=error,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return self._fail("Command timed out (30s)")
        except Exception as e:
            return self._fail(str(e))
