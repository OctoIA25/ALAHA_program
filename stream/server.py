import asyncio
import json
import logging
import time
import base64
import io
from typing import Optional

import mss
import websockets
from PIL import Image
import pyautogui

from core.logger import get_logger

log = get_logger("stream.server")

# Config
FPS = 8
FRAME_INTERVAL = 1.0 / FPS
WEBSOCKET_PORT = 8765

class ScreenStreamServer:
    def __init__(self):
        self.clients = set()
        self.running = False
        self.frame_count = 0
        
    async def register(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        log.info(f"Client connected. Total clients: {len(self.clients)}")
        
    async def unregister(self, websocket):
        """Unregister a client."""
        self.clients.discard(websocket)
        log.info(f"Client disconnected. Total clients: {len(self.clients)}")
        
    def capture_frame(self) -> tuple[str, tuple[int, int]]:
        """Capture screen frame and get cursor position."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                
                # Get cursor position
                cursor_x, cursor_y = pyautogui.position()
                
                # Compress frame
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=60, optimize=True)
                encoded = base64.b64encode(buffer.getvalue()).decode()
                
                return encoded, (cursor_x, cursor_y), (screenshot.width, screenshot.height)
        except Exception as e:
            log.error(f"Frame capture failed: {e}")
            return "", (0, 0), (0, 0)
            
    async def broadcast_frame(self):
        """Capture and broadcast frame to all connected clients."""
        frame_data, cursor_pos, screen_size = self.capture_frame()
        if not frame_data:
            return
            
        message = {
            "type": "frame",
            "frame": frame_data,
            "cursor": cursor_pos,
            "screen_size": screen_size,
            "timestamp": time.time(),
            "frame_id": self.frame_count
        }
        
        # Send to all clients
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients],
                return_exceptions=True
            )
            self.frame_count += 1
            
    async def handle_client(self, websocket, path):
        """Handle individual client connection."""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Handle any client messages if needed
                data = json.loads(message)
                log.debug(f"Received client message: {data.get('type', 'unknown')}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
            
    async def stream_loop(self):
        """Main streaming loop."""
        log.info(f"Starting screen stream at {FPS} FPS on port {WEBSOCKET_PORT}")
        self.running = True
        
        while self.running:
            start_time = time.time()
            await self.broadcast_frame()
            
            # Maintain FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, FRAME_INTERVAL - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
    async def start_server(self):
        """Start the WebSocket server and streaming loop."""
        # Start WebSocket server
        server = await websockets.serve(self.handle_client, "localhost", WEBSOCKET_PORT)
        log.info(f"WebSocket server started on ws://localhost:{WEBSOCKET_PORT}")
        
        # Start streaming loop
        await self.stream_loop()
        
    def stop(self):
        """Stop the streaming server."""
        self.running = False
        log.info("Stream server stopped")

async def main():
    server = ScreenStreamServer()
    try:
        await server.start_server()
    except KeyboardInterrupt:
        log.info("Shutting down stream server...")
        server.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
