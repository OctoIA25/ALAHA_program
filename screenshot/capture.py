import base64
import io
from typing import Optional

import mss
from PIL import Image, ImageDraw, ImageFilter

from core.logger import get_logger

log = get_logger("screenshot")

MAX_WIDTH = 1366
MAX_HEIGHT = 768
JPEG_QUALITY = 82


def get_native_size() -> tuple[int, int]:
    """Return the native screen resolution (width, height). Refreshed each call."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            return monitor["width"], monitor["height"]
    except Exception:
        return 1920, 1080


def capture_screenshot(
    highlight_x: Optional[int] = None,
    highlight_y: Optional[int] = None,
    radius: int = 30,
) -> dict:
    """Capture screen, optionally highlight a point, resize for LLM.

    Returns dict with keys:
      image    – base64-encoded JPEG string
      sent_w   – width of the resized image sent to the LLM
      sent_h   – height of the resized image sent to the LLM
      native_w – real screen width in pixels
      native_h – real screen height in pixels

    Highlight coordinates are in NATIVE screen space.
    The LLM should report coordinates in sent_w x sent_h space;
    the orchestrator scales them back to native before executing.
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

        sent_w, sent_h = native_w, native_h
        if native_w > MAX_WIDTH or native_h > MAX_HEIGHT:
            ratio = min(MAX_WIDTH / native_w, MAX_HEIGHT / native_h)
            sent_w = int(native_w * ratio)
            sent_h = int(native_h * ratio)
            img = img.resize((sent_w, sent_h), Image.LANCZOS)
            img = img.filter(ImageFilter.SHARPEN)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        log.debug(f"Screenshot captured: native={native_w}x{native_h}, sent={sent_w}x{sent_h}, {len(encoded)} chars base64")
        return {
            "image": encoded,
            "sent_w": sent_w,
            "sent_h": sent_h,
            "native_w": native_w,
            "native_h": native_h,
        }
    except Exception as e:
        log.error(f"Screenshot capture failed: {e}")
        return {"image": "", "sent_w": 0, "sent_h": 0, "native_w": 0, "native_h": 0}
