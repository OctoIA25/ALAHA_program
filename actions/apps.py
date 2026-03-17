import shutil
import subprocess
import sys

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.apps")

_IS_LINUX = sys.platform.startswith("linux")

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

LINUX_APP_MAP = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "google-chrome": ["google-chrome", "google-chrome-stable"],
    "chromium": ["chromium-browser", "chromium"],
    "firefox": ["firefox"],
    "edge": ["microsoft-edge", "microsoft-edge-stable"],
    "brave": ["brave-browser", "brave-browser-stable"],
    "opera": ["opera"],
    "terminal": ["gnome-terminal", "xfce4-terminal", "konsole", "xterm"],
    "files": ["nautilus", "thunar", "nemo", "dolphin", "pcmanfm"],
    "nautilus": ["nautilus"],
    "thunar": ["thunar"],
    "calculator": ["gnome-calculator", "galculator", "kcalc"],
    "text-editor": ["gedit", "xed", "mousepad", "kate", "pluma"],
    "gedit": ["gedit"],
    "code": ["code", "codium"],
    "vscode": ["code", "codium"],
    "libreoffice": ["libreoffice"],
    "writer": ["libreoffice --writer"],
    "calc": ["libreoffice --calc"],
    "gimp": ["gimp"],
    "vlc": ["vlc"],
    "spotify": ["spotify"],
    "telegram": ["telegram-desktop"],
    "discord": ["discord"],
    "slack": ["slack"],
    "obs": ["obs"],
    "settings": ["gnome-control-center", "xfce4-settings-manager"],
}


def _find_linux_executable(app: str) -> str | None:
    """Find the first available executable for a Linux app name."""
    candidates = LINUX_APP_MAP.get(app.lower(), [app])
    for candidate in candidates:
        parts = candidate.split()
        binary = parts[0]
        if shutil.which(binary):
            return candidate
    return None


class OpenAppAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        app = params.get("app", "")
        try:
            if _IS_LINUX:
                executable = _find_linux_executable(app)
                if not executable:
                    log.warning(f"App not found directly, trying xdg-open: {app}")
                    subprocess.Popen(
                        ["xdg-open", app],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    return self._ok(app=app, method="xdg-open")

                subprocess.Popen(
                    executable.split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                log.info(f"Opened app (Linux): {app} -> {executable}")
                return self._ok(app=app, executable=executable)
            else:
                executable = WINDOWS_APP_MAP.get(app.lower(), app)
                subprocess.Popen(
                    ["start", "", executable],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info(f"Opened app (Windows): {app} -> {executable}")
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
                env=None,
            )
            output = result.stdout[:2000] if result.stdout else ""
            error = result.stderr[:500] if result.stderr else ""
            log.info(f"Command executed: {command[:80]}")
            return self._ok(
                output=output,
                error=error,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return self._fail("Command timed out (30s)")
        except Exception as e:
            return self._fail(str(e))
