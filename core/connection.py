import asyncio
import json
from typing import Optional, Callable

import websockets
from websockets.exceptions import ConnectionClosed

from core.logger import get_logger
from core.heartbeat import heartbeat_loop

log = get_logger("connection")

RECONNECT_DELAY = 5  # seconds between reconnection attempts


class ConnectionClient:
    """WebSocket client that connects outbound to the ALAHA Dashboard."""

    def __init__(self, agent_id: str, dashboard_url: str, api_key: str):
        self.agent_id = agent_id
        self.dashboard_url = dashboard_url.rstrip("/")
        self.api_key = api_key
        self.ws = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._connect_task: Optional[asyncio.Task] = None
        self._on_message: Optional[Callable] = None
        self._on_status_change: Optional[Callable] = None
        self._status = "offline"

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

    def update_config(self, dashboard_url: str, api_key: str) -> None:
        """Update connection settings (takes effect on next reconnect)."""
        self.dashboard_url = dashboard_url.rstrip("/")
        self.api_key = api_key

    def _build_uri(self) -> str:
        base = self.dashboard_url
        # Convert http(s) to ws(s) if needed
        if base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        elif base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif not base.startswith("ws://") and not base.startswith("wss://"):
            base = "ws://" + base
        return f"{base}/ws/agent/{self.agent_id}/?key={self.api_key}"

    async def _run_connection(self) -> None:
        while self._running:
            if not self.dashboard_url or not self.api_key:
                log.warning("Dashboard URL or API key not configured. Waiting...")
                self._set_status("not_configured")
                await asyncio.sleep(RECONNECT_DELAY)
                continue

            uri = self._build_uri()
            log.info(f"Connecting to Dashboard: {self.dashboard_url}")
            self._set_status("connecting")

            try:
                async with websockets.connect(uri, ping_interval=None) as ws:
                    self.ws = ws
                    self._set_status("online")
                    log.info(f"Connected to Dashboard | Agent ID: {self.agent_id}")

                    self._heartbeat_task = asyncio.create_task(
                        heartbeat_loop(ws, self.agent_id)
                    )

                    try:
                        async for raw in ws:
                            try:
                                msg = json.loads(raw)
                                log.debug(f"Received: {msg.get('type', 'unknown')}")
                                if self._on_message:
                                    await self._on_message(msg)
                            except json.JSONDecodeError:
                                log.warning("Received non-JSON message")
                    except ConnectionClosed as e:
                        log.warning(f"Connection closed: {e}")
                    except Exception as e:
                        log.error(f"Connection handler error: {e}")
                    finally:
                        if self._heartbeat_task:
                            self._heartbeat_task.cancel()
                            self._heartbeat_task = None

            except (OSError, ConnectionRefusedError, websockets.exceptions.InvalidURI,
                    websockets.exceptions.InvalidHandshake) as e:
                log.warning(f"Could not connect: {e}")
            except Exception as e:
                log.error(f"Unexpected connection error: {e}")
            finally:
                self.ws = None
                if self._running:
                    self._set_status("reconnecting")
                    log.info(f"Reconnecting in {RECONNECT_DELAY}s...")
                    await asyncio.sleep(RECONNECT_DELAY)

        self._set_status("offline")

    async def start(self) -> None:
        self._running = True
        self._connect_task = asyncio.create_task(self._run_connection())
        log.info(f"ConnectionClient started | Agent ID: {self.agent_id}")

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._connect_task:
            self._connect_task.cancel()
            self._connect_task = None
        if self.ws:
            await self.ws.close()
            self.ws = None
        self._set_status("offline")
        log.info("ConnectionClient stopped")

    async def send(self, data: dict) -> None:
        if self.ws:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                log.warning(f"Send failed: {e}")
        else:
            log.warning("Cannot send: not connected to Dashboard")
