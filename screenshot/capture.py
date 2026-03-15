import base64
import io
from typing import Optional

import mss
from PIL import Image, ImageDraw

from core.logger import get_logger

log = get_logger("screenshot")

TARGET_SIZE = (1280, 720)


def capture_screenshot(
    highlight_x: Optional[int] = None,
    highlight_y: Optional[int] = None,
    radius: int = 30,
) -> str:
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            original_w = monitor["width"]
            original_h = monitor["height"]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)

        img = img.resize(TARGET_SIZE)

        if highlight_x is not None and highlight_y is not None:
            scale_x = TARGET_SIZE[0] / original_w
            scale_y = TARGET_SIZE[1] / original_h
            hx = int(highlight_x * scale_x)
            hy = int(highlight_y * scale_y)
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [hx - radius, hy - radius, hx + radius, hy + radius],
                outline="red",
                width=3,
            )

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        log.debug(f"Screenshot captured: {len(encoded)} chars base64")
        return encoded
    except Exception as e:
        log.error(f"Screenshot capture failed: {e}")
        return ""
