"""MATRIX WebSocket Real-Time Connection Manager.
Broadcasts live telemetries, agent status, and holographic animation states to frontend clients.
"""
from typing import List, Dict, Any
from fastapi import WebSocket
import asyncio
import psutil
from config.logging_config import get_logger

logger = get_logger("websocket")


class ConnectionManager:
    """Manages active WebSocket connections for UI and mobile companions."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._telemetry_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

        # Send initial handshake state
        await websocket.send_json({
            "type": "handshake",
            "payload": {
                "system_status": "ONLINE",
                "hologram_state": "idle",
                "message": "MATRIX Core Link Established"
            }
        })

        if not self._telemetry_task or self._telemetry_task.done():
            self._telemetry_task = asyncio.create_task(self._broadcast_telemetry_loop())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all active clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                self.disconnect(connection)

    async def _broadcast_telemetry_loop(self):
        """Periodic background broadcast of verified hardware metrics (every 2s)."""
        logger.info("Started real-time WebSocket telemetry loop.")
        try:
            while self.active_connections:
                vm = psutil.virtual_memory()
                cpu_p = psutil.cpu_percent(interval=None)

                payload = {
                    "type": "telemetry_update",
                    "payload": {
                        "cpu_percent": cpu_p,
                        "ram_percent": vm.percent,
                        "ram_used_mb": round(vm.used / (1024 * 1024), 1),
                        "ram_available_mb": round(vm.available / (1024 * 1024), 1),
                        "status": "nominal" if vm.percent < 85 else "warning"
                    }
                }
                await self.broadcast(payload)
                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in telemetry loop: {e}")
        finally:
            logger.info("Stopped real-time WebSocket telemetry loop.")


# Singleton connection manager
ws_manager = ConnectionManager()
