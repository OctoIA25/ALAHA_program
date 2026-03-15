from typing import Optional, Callable, Awaitable

from core.logger import get_logger

log = get_logger("dispatcher")


class Dispatcher:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, msg_type: str, handler: Callable) -> None:
        self._handlers[msg_type] = handler
        log.debug(f"Registered handler for '{msg_type}'")

    async def dispatch(self, message: dict) -> None:
        msg_type = message.get("type")
        if not msg_type:
            log.warning("Message without type field, ignoring")
            return

        handler = self._handlers.get(msg_type)
        if handler:
            log.info(f"Dispatching '{msg_type}'")
            try:
                await handler(message)
            except Exception as e:
                log.error(f"Handler error for '{msg_type}': {e}")
        else:
            log.warning(f"No handler for message type '{msg_type}'")
