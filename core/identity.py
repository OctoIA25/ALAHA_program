from core import config as cfg
from core.logger import get_logger

log = get_logger("identity")


def get_or_create_snowflake_id() -> str:
    sid = cfg.get_snowflake_id() or ""
    if sid:
        log.info(f"Loaded configured snowflake_id: {sid}")
        return sid
    log.info("No snowflake_id configured yet")
    return ""
