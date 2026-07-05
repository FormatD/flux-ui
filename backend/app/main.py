import os
import json
import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Scope, Receive, Send

from .logger import setup_logger
from .database import init_db
from .websocket_manager import manager, progress_callback
from .services.task_queue import task_queue

from .routers import (
    generate,
    images,
    prompts,
    models,
    tasks,
    settings,
    upload,
)

logger = setup_logger("mflux")


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = [0]

        async def _send(event: dict):
            if event["type"] == "http.response.start":
                status_code[0] = event["status"]
            await send(event)

        await self.app(scope, receive, _send)

        elapsed = time.time() - start
        status = status_code[0]
        msg = f"{method:6s} {path:40s} {status:3d}  {elapsed*1000:6.0f}ms"
        if elapsed > 2:
            logger.warning(msg)
        else:
            logger.info(msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("MFlux Studio starting...")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Output dir: {os.path.abspath(os.getenv('OUTPUT_DIR', './output'))}")
    logger.info(f"Upload dir: {os.path.abspath(os.getenv('UPLOAD_DIR', './uploads'))}")

    init_db()
    logger.info("Database initialized")

    manager.set_loop(asyncio.get_event_loop())
    task_queue.set_progress_callback(progress_callback)
    task_queue.set_broadcast_callback(lambda msg: asyncio.run_coroutine_threadsafe(
        manager.broadcast(msg), manager._loop
    ))
    logger.info("Task queue and WebSocket manager ready")

    yield

    logger.info("Shutting down MFlux Studio...")
    task_queue.stop()
    logger.info("Task queue stopped")


app = FastAPI(title="MFlux Studio", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLogMiddleware)

app.include_router(generate.router)
app.include_router(images.router)
app.include_router(prompts.router)
app.include_router(models.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(upload.router)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/api/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/api/files", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client = ws.client
    logger.info(f"WebSocket connection from {client}")
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "")
            if msg_type == "ping":
                await manager.send_to(ws, {"type": "pong"})
            elif msg_type:
                logger.debug(f"WS message from {client}: {msg_type}")
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client}")
        manager.disconnect(ws)
    except Exception as e:
        logger.warning(f"WebSocket error ({client}): {e}")
        manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
