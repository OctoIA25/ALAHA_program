import json
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger("config")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _load_raw() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_raw(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_snowflake_id() -> Optional[str]:
    cfg = _load_raw()
    return cfg.get("snowflake_id")


def get_autostart() -> bool:
    cfg = _load_raw()
    return cfg.get("autostart", False)


def set_autostart(enabled: bool) -> None:
    cfg = _load_raw()
    cfg["autostart"] = enabled
    _save_raw(cfg)
    log.info(f"Autostart set to {enabled}")
