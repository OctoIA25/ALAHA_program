import asyncio
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import get_logger
from core.identity import get_or_create_snowflake_id
from core.connection import ConnectionClient
from core.dispatcher import Dispatcher
from core.orchestrator import Orchestrator
from llm.client import LLMClient
from ui.main_window import MainWindow

log = get_logger("main")


class ALAHAProgram:
    def __init__(self):
        self.snowflake_id = get_or_create_snowflake_id()
        self.loop = asyncio.new_event_loop()
        self.connection = ConnectionClient(self.snowflake_id)
        self.llm = LLMClient()
        self.dispatcher = Dispatcher()
        self.orchestrator = Orchestrator(self.connection, self.llm)

        self._setup_dispatcher()

        self.connection.set_on_message(self.dispatcher.dispatch)
        self.connection.set_on_status_change(self._on_status_change)

        self.window = MainWindow(
            snowflake_id=self.snowflake_id,
            on_reconnect=self._request_reconnect,
        )

    def _setup_dispatcher(self) -> None:
        self.dispatcher.register("configure_llm", self._handle_configure_llm)
        self.dispatcher.register("instruction", self.orchestrator.handle_instruction)
        self.dispatcher.register("execute_actions", self.orchestrator.handle_execute_actions)
        self.dispatcher.register("ping", self._handle_ping)

    async def _handle_configure_llm(self, message: dict) -> None:
        llm_api_key = message.get("api_key", "")
        base_url = message.get("base_url", "")
        model = message.get("model", "")

        if not all([llm_api_key, base_url, model]):
            log.error("Incomplete LLM configuration received")
            return

        self.llm.configure(llm_api_key, base_url, model)
        log.info(f"LLM configured via Dashboard: model={model}")
        self.window.update_llm_status(model)

        await self.connection.send({
            "type": "llm_configured",
            "agent_id": self.snowflake_id,
            "model": model,
        })

    async def _handle_ping(self, message: dict) -> None:
        await self.connection.send({
            "type": "pong",
            "agent_id": self.snowflake_id,
        })

    def _on_status_change(self, status: str) -> None:
        self.window.update_status(status)

    def _request_reconnect(self, dashboard_url: str, api_key: str) -> None:
        asyncio.run_coroutine_threadsafe(
            self.connection.reconnect(dashboard_url, api_key),
            self.loop,
        )

    async def _start_connection(self) -> None:
        await self.connection.start()

    async def _shutdown(self) -> None:
        await self.connection.stop()
        await self.llm.close()

    def _run_async_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self) -> None:
        log.info(f"ALAHA Program starting | ID: {self.snowflake_id}")
        log.info("Outbound WebSocket client enabled")

        async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        async_thread.start()

        asyncio.run_coroutine_threadsafe(self._start_connection(), self.loop)

        try:
            self.window.run()
        except KeyboardInterrupt:
            log.info("Shutting down...")
        finally:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)
            log.info("ALAHA Program stopped")


def main():
    app = ALAHAProgram()
    app.run()


if __name__ == "__main__":
    main()
