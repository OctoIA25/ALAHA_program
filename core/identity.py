import json
import time
import random
from pathlib import Path

from core.logger import get_logger

log = get_logger("identity")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

_EPOCH = 1700000000000  # custom epoch (ms)
_SEQUENCE_BITS = 12
_MACHINE_BITS = 10
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1
_MAX_MACHINE = (1 << _MACHINE_BITS) - 1

_machine_id = random.randint(0, _MAX_MACHINE)
_last_ts = -1
_sequence = 0


def _current_ms() -> int:
    return int(time.time() * 1000)


def _generate_snowflake() -> str:
    global _last_ts, _sequence
    ts = _current_ms() - _EPOCH
    if ts == _last_ts:
        _sequence = (_sequence + 1) & _MAX_SEQUENCE
        if _sequence == 0:
            while ts <= _last_ts:
                ts = _current_ms() - _EPOCH
    else:
        _sequence = 0
    _last_ts = ts
    sid = (ts << (_MACHINE_BITS + _SEQUENCE_BITS)) | (_machine_id << _SEQUENCE_BITS) | _sequence
    return str(sid)


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_or_create_snowflake_id() -> str:
    cfg = _load_config()
    sid = cfg.get("snowflake_id")
    if sid:
        log.info(f"Loaded existing snowflake_id: {sid}")
        return sid
    sid = _generate_snowflake()
    cfg["snowflake_id"] = sid
    _save_config(cfg)
    log.info(f"Generated new snowflake_id: {sid}")
    return sid
