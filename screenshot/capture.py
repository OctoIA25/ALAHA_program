import base64
import io
from typing import Optional

import mss
from PIL import Image, ImageDraw

from core.logger import get_logger

log = get_logger("screenshot")

TARGET_SIZE = (1280, 720)  # kept for backward compat, not used for capture


def capture_screenshot(
    highlight_x: Optional[int] = None,
    highlight_y: Optional[int] = None,
    radius: int = 30,
) -> str:
    """Capture screen at native resolution. Coordinates are in native screen space."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)

        if highlight_x is not None and highlight_y is not None:
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [highlight_x - radius, highlight_y - radius,
                 highlight_x + radius, highlight_y + radius],
                outline="red",
                width=3,
            )

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        log.debug(f"Screenshot captured: {raw.width}x{raw.height}, {len(encoded)} chars base64")
        return encoded
    except Exception as e:
        log.error(f"Screenshot capture failed: {e}")
        return ""
