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


def set_snowflake_id(snowflake_id: str) -> None:
    cfg = _load_raw()
    cfg["snowflake_id"] = snowflake_id.strip()
    _save_raw(cfg)
    log.info(f"Snowflake ID set to {snowflake_id.strip()}")


def get_dashboard_url() -> str:
    cfg = _load_raw()
    return cfg.get("dashboard_url", "")


def set_dashboard_url(url: str) -> None:
    cfg = _load_raw()
    cfg["dashboard_url"] = url.strip()
    _save_raw(cfg)
    log.info(f"Dashboard URL set to {url.strip()}")


def get_api_key() -> str:
    cfg = _load_raw()
    return cfg.get("api_key", "")


def set_api_key(key: str) -> None:
    cfg = _load_raw()
    cfg["api_key"] = key.strip()
    _save_raw(cfg)
    log.info("API key updated")


def get_autostart() -> bool:
    cfg = _load_raw()
    return cfg.get("autostart", False)


def set_autostart(enabled: bool) -> None:
    cfg = _load_raw()
    cfg["autostart"] = enabled
    _save_raw(cfg)
    log.info(f"Autostart set to {enabled}")
