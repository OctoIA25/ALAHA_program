import base64
import io
from typing import Optional

import mss
from PIL import Image, ImageDraw, ImageFilter

from core.logger import get_logger

log = get_logger("screenshot")

MAX_WIDTH = 1280
MAX_HEIGHT = 720
JPEG_QUALITY = 75


def _get_screen_size() -> tuple[int, int]:
    """Return the native screen resolution (width, height)."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            return monitor["width"], monitor["height"]
    except Exception:
        return 1920, 1080


_NATIVE_W, _NATIVE_H = _get_screen_size()


def get_native_size() -> tuple[int, int]:
    """Public accessor for the native screen resolution."""
    return _NATIVE_W, _NATIVE_H


def capture_screenshot(
    highlight_x: Optional[int] = None,
    highlight_y: Optional[int] = None,
    radius: int = 30,
) -> str:
    """Capture screen, optionally highlight a point, resize for LLM, return base64 JPEG.

    Coordinates are always in NATIVE screen space (the real pixel coords).
    The image is resized to MAX_WIDTH x MAX_HEIGHT for efficient LLM processing,
    but the coordinate system the LLM sees matches the native resolution.
    """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)
            native_w, native_h = raw.width, raw.height

        if highlight_x is not None and highlight_y is not None:
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [highlight_x - radius, highlight_y - radius,
                 highlight_x + radius, highlight_y + radius],
                outline="red",
                width=4,
            )

        if native_w > MAX_WIDTH or native_h > MAX_HEIGHT:
            ratio = min(MAX_WIDTH / native_w, MAX_HEIGHT / native_h)
            new_w = int(native_w * ratio)
            new_h = int(native_h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img = img.filter(ImageFilter.SHARPEN)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        log.debug(f"Screenshot captured: native={native_w}x{native_h}, sent={img.width}x{img.height}, {len(encoded)} chars base64")
        return encoded
    except Exception as e:
        log.error(f"Screenshot capture failed: {e}")
        return ""
