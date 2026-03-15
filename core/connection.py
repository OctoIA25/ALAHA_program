import asyncio
import json
from typing import Optional, Callable

import websockets

from core.logger import get_logger
from core.heartbeat import heartbeat_loop

log = get_logger("connection")

DEFAULT_PORT = 7778


class ConnectionServer:
    """Local WebSocket server that the ALAHA Dashboard connects to."""

    def __init__(self, agent_id: str, port: int = DEFAULT_PORT):
        self.agent_id = agent_id
        self.port = port
        self.ws = None
        self._server = None
        self._heartbeat_task: Optional[asyncio.Task] = None
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

    async def _handle_client(self, ws) -> None:
        remote = ws.remote_address
        log.info(f"Dashboard connected from {remote}")
        self.ws = ws
        self._set_status("online")

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
        except websockets.ConnectionClosed as e:
            log.warning(f"Dashboard disconnected: {e}")
        except Exception as e:
            log.error(f"Client handler error: {e}")
        finally:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            self.ws = None
            self._set_status("waiting")
            log.info("Waiting for Dashboard to reconnect...")

    async def start(self) -> None:
        self._set_status("waiting")
        log.info(f"WebSocket server starting on 0.0.0.0:{self.port}")
        self._server = await websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self.port,
        )
        log.info(f"Listening on ws://0.0.0.0:{self.port}  |  Agent ID: {self.agent_id}")

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self.ws:
            await self.ws.close()
            self.ws = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._set_status("offline")
        log.info("Server stopped")

    async def send(self, data: dict) -> None:
        if self.ws:
            await self.ws.send(json.dumps(data))
        else:
            log.warning("Cannot send: no Dashboard connected")
