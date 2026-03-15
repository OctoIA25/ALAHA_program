import secrets

from core import config as cfg
from core.logger import get_logger

log = get_logger("identity")


def _generate_snowflake_id() -> str:
    return secrets.token_hex(16)


def get_or_create_snowflake_id() -> str:
    sid = cfg.get_snowflake_id() or ""
    if sid:
        log.info(f"Loaded configured snowflake_id: {sid}")
        return sid
    sid = _generate_snowflake_id()
    cfg.set_snowflake_id(sid)
    log.info(f"Generated new snowflake_id: {sid}")
    return sid
