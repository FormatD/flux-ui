import json
import asyncio
import threading
from typing import Set
from fastapi import WebSocket

from .logger import get_logger

log = get_logger("ws")


class ConnectionManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = threading.Lock()
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        with self._lock:
            self._connections.add(ws)
        log.debug("WS connected (%s total)", len(self._connections))

    def disconnect(self, ws: WebSocket):
        with self._lock:
            self._connections.discard(ws)
        log.debug("WS disconnected (%s remaining)", len(self._connections))

    async def broadcast(self, message: dict):
        dead = set()
        with self._lock:
            conns = set(self._connections)
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception as e:
                log.debug("WS send error: %s", e)
                dead.add(ws)
        with self._lock:
            self._connections -= dead

    async def send_to(self, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception:
            with self._lock:
                self._connections.discard(ws)


manager = ConnectionManager()


def scan_progress_callback(task_id: str, phase_or_model: str, message: str, current: int, total: int, elapsed: float):
    """Broadcast scan progress via WebSocket. Reuses model_scanner's callback signature.

    The callback from model_scanner passes (model_name, message, current, total, elapsed).
    We repack it with type="scan_progress" so the frontend can distinguish from generation progress.
    """
    pct = int((current / max(total, 1)) * 100)
    coro = manager.broadcast({
        "type": "scan_progress",
        "task_id": task_id,
        "phase_or_model": phase_or_model,
        "message": message,
        "current_step": current,
        "total_steps": total,
        "elapsed": round(elapsed, 1),
        "percent": min(pct, 100),
    })
    try:
        loop = manager._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception as e:
        log.warning("scan progress broadcast failed: %s", e)


def progress_callback(task_id: str, message: str, current: int, total: int, elapsed: float):
    percent = int((current / max(total, 1)) * 100)
    coro = manager.broadcast({
        "type": "progress",
        "task_id": task_id,
        "message": message,
        "current_step": current,
        "total_steps": total,
        "elapsed": round(elapsed, 1),
        "percent": min(percent, 100),
    })
    try:
        loop = manager._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception as e:
        log.warning("progress broadcast failed: %s", e)
