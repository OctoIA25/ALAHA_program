import sys
import subprocess

from actions.base import ActionExecutor
from core.logger import get_logger

log = get_logger("actions.windows")


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _wmctrl_available() -> bool:
    try:
        subprocess.run(["wmctrl", "-l"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _xdotool_available() -> bool:
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _focus_linux(title: str) -> tuple[bool, str]:
    if _xdotool_available():
        r = subprocess.run(
            ["xdotool", "search", "--name", title, "windowactivate", "--sync"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, title
        return False, r.stderr.strip() or f"Window not found: {title}"
    if _wmctrl_available():
        r = subprocess.run(
            ["wmctrl", "-a", title],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, title
        return False, r.stderr.strip() or f"Window not found: {title}"
    return False, "Neither xdotool nor wmctrl found. Install one: sudo apt install xdotool"


def _close_linux(title: str) -> tuple[bool, str]:
    if _xdotool_available():
        r = subprocess.run(
            ["xdotool", "search", "--name", title, "windowclose"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or f"Window not found: {title}"
    if _wmctrl_available():
        r = subprocess.run(
            ["wmctrl", "-c", title],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or f"Window not found: {title}"
    return False, "Neither xdotool nor wmctrl found. Install one: sudo apt install xdotool"


def _maximize_linux(title: str) -> tuple[bool, str]:
    if _wmctrl_available():
        r = subprocess.run(
            ["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or f"Window not found: {title}"
    if _xdotool_available():
        r = subprocess.run(
            ["xdotool", "search", "--name", title, "windowmaximize"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or f"Window not found: {title}"
    return False, "Neither wmctrl nor xdotool found. Install one: sudo apt install wmctrl"


def _ps_window_op(operation: str, title: str) -> tuple[bool, str]:
    scripts = {
        "focus": (
            f"Add-Type -AssemblyName Microsoft.VisualBasic; "
            f"[Microsoft.VisualBasic.Interaction]::AppActivate('{title}')"
        ),
        "close": (
            f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | "
            f"Select-Object -First 1; if ($p) {{ $p.CloseMainWindow() }}"
        ),
        "maximize": (
            f"Add-Type @'\n"
            f"using System; using System.Runtime.InteropServices;\n"
            f"public class Win {{ [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int n); "
            f"[DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string c, string t); }}\n"
            f"'@; "
            f"$h = [Win]::FindWindow($null, '{title}'); "
            f"if ($h -ne [IntPtr]::Zero) {{ [Win]::ShowWindow($h, 3) }}"
        ),
    }
    script = scripts.get(operation, "")
    if not script:
        return False, f"Unknown operation: {operation}"
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return True, title
        return False, r.stderr.strip() or f"Window not found: {title}"
    except FileNotFoundError:
        return False, "powershell not found"
    except Exception as e:
        return False, str(e)


class FocusWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            if _is_linux():
                ok, msg = _focus_linux(title)
            else:
                ok, msg = _ps_window_op("focus", title)
            if not ok:
                return self._fail(msg)
            log.info(f"Focused window: {title}")
            return self._ok(title=title)
        except Exception as e:
            return self._fail(str(e))


class CloseWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            if _is_linux():
                ok, msg = _close_linux(title)
            else:
                ok, msg = _ps_window_op("close", title)
            if not ok:
                return self._fail(msg)
            log.info(f"Closed window: {title}")
            return self._ok()
        except Exception as e:
            return self._fail(str(e))


class MaximizeWindowAction(ActionExecutor):
    async def execute(self, params: dict) -> dict:
        title = params.get("title", "")
        try:
            if _is_linux():
                ok, msg = _maximize_linux(title)
            else:
                ok, msg = _ps_window_op("maximize", title)
            if not ok:
                return self._fail(msg)
            log.info(f"Maximized window: {title}")
            return self._ok()
        except Exception as e:
            return self._fail(str(e))
