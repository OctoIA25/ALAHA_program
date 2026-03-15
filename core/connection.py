import asyncio
import json
from typing import Optional, Callable
from urllib.parse import quote, urlencode, urlparse

import websockets

from core import config as cfg
from core.heartbeat import heartbeat_loop
from core.logger import get_logger

log = get_logger("connection")

RECONNECT_DELAY_SECONDS = 5


class ConnectionClient:
    """Outbound WebSocket client that connects the Program to the Dashboard."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.ws = None
        self._runner_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._on_message: Optional[Callable] = None
        self._on_status_change: Optional[Callable] = None
        self._status = "offline"
        self._stop_requested = False
        self._dashboard_url = cfg.get_dashboard_url()
        self._api_key = cfg.get_api_key()

    @property
    def status(self) -> str:
        return self._status

    def _set_status(self, status: str) -> None:
        self._status = status
        log.info(f"Status: {status}")
        if self._on_status_change:
            try:
                self._on_status_change(status)
            except Exception:
                pass

    def set_on_message(self, callback: Callable) -> None:
        self._on_message = callback

    def set_on_status_change(self, callback: Callable) -> None:
        self._on_status_change = callback

    def update_settings(self, snowflake_id: str, dashboard_url: str, api_key: str) -> None:
        self.agent_id = snowflake_id.strip()
        self._dashboard_url = dashboard_url.strip()
        self._api_key = api_key.strip()
        cfg.set_snowflake_id(self.agent_id)
        cfg.set_dashboard_url(self._dashboard_url)
        cfg.set_api_key(self._api_key)

    def _build_ws_url(self) -> str:
        parsed = urlparse(self._dashboard_url.strip())
        if parsed.scheme not in {"http", "https", "ws", "wss"} or not parsed.netloc:
            raise ValueError("Dashboard URL inválida")

        scheme = "wss" if parsed.scheme in {"https", "wss"} else "ws"
        query = urlencode({"key": self._api_key})
        return f"{scheme}://{parsed.netloc}/ws/agent/{quote(self.agent_id)}/?{query}"

    async def _run_forever(self) -> None:
        while not self._stop_requested:
            if not self.agent_id or not self._dashboard_url or not self._api_key:
                self._set_status("waiting_config")
                await asyncio.sleep(1)
                continue

            try:
                target_url = self._build_ws_url()
            except Exception as e:
                log.warning(f"Configuração de conexão inválida: {e}")
                self._set_status("error")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

            self._set_status("connecting")
            log.info(f"Connecting to Dashboard at {target_url}")

            try:
                async with websockets.connect(target_url, ping_interval=20, ping_timeout=60) as ws:
                    self.ws = ws
                    self._set_status("online")
                    self._heartbeat_task = asyncio.create_task(heartbeat_loop(ws, self.agent_id))

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            log.debug(f"Received: {msg.get('type', 'unknown')}")
                            if self._on_message:
                                await self._on_message(msg)
                        except json.JSONDecodeError:
                            log.warning("Received non-JSON message")
            except asyncio.CancelledError:
                break
            except websockets.ConnectionClosed as e:
                log.warning(f"Dashboard connection closed: {e}")
            except Exception as e:
                log.error(f"Dashboard connection error: {e}")
            finally:
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    self._heartbeat_task = None
                self.ws = None

            if not self._stop_requested:
                self._set_status("reconnecting")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def start(self) -> None:
        self._stop_requested = False
        if not self._runner_task or self._runner_task.done():
            self._runner_task = asyncio.create_task(self._run_forever())

    async def reconnect(self, snowflake_id: str, dashboard_url: str, api_key: str) -> None:
        self.update_settings(snowflake_id, dashboard_url, api_key)
        if self.ws:
            await self.ws.close()
        if not self._runner_task or self._runner_task.done():
            await self.start()

    async def stop(self) -> None:
        self._stop_requested = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self.ws:
            await self.ws.close()
            self.ws = None
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except Exception:
                pass
            self._runner_task = None
        self._set_status("offline")
        log.info("Connection client stopped")

    async def send(self, data: dict) -> None:
        if self.ws:
            await self.ws.send(json.dumps(data))
        else:
            log.warning("Cannot send: no Dashboard connected")


ConnectionServer = ConnectionClient
