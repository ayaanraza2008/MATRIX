"""MATRIX Main FastAPI Application Server.
Provides REST APIs, WebSocket real-time channel, error handlers, and lifecycle hooks.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import time
import uuid

from config.settings import settings
from config.logging_config import get_logger
from database.init_db import init_database
from security.authentication.api_access import is_trusted_client, matches_api_token
from api.routes import (
    health, system, sessions, capabilities, devices, memory, voice, vision, repositories,
    automation, files, audit, developer, integrations, airtouch, telephony, briefing, security
)
from api.websocket.manager import ws_manager

logger = get_logger("server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info(f"Initiating {settings.app_name} v{settings.version} [{settings.env}]...")
    settings.initialize_directories()

    # Initialize SQLite database schema
    db_ready = await init_database()
    if db_ready:
        logger.info(f"Core database operational at {settings.data_dir / 'matrix.db'}")
    else:
        logger.error("Database initialization encountered an error!")

    # Optional interactive subsystems: voice broker, microphone listener, model warm-up.
    # These depend on audio hardware and are expected to fail on headless hosts.
    try:
        from voice.conversation.manager import hands_free_manager
        from core.orchestrator import orchestrator

        def _broadcast_to_ws(evt):
            asyncio.create_task(ws_manager.broadcast(evt))

        hands_free_manager.subscribe(_broadcast_to_ws)
        orchestrator.subscribe_progress(_broadcast_to_ws)
        logger.info("Hands-Free voice and orchestrator telemetry wired to WebSocket broker.")

        from voice.mic_listener import mic_listener
        mic_listener.start(asyncio.get_running_loop())
        logger.info("Persistent background native microphone listener service started.")

        from core.model_manager import model_manager
        asyncio.create_task(asyncio.to_thread(model_manager.load_local_model))
        logger.info("Local LLM model background warm-up task dispatched.")
    except Exception as e:
        logger.warning(f"Optional voice/model subsystems unavailable on this host: {e}")

    # Persistent background scheduler and Autonomy Core (must start on every host).
    try:
        from automation.scheduler.engine import background_scheduler
        await background_scheduler.start()
        from core.autonomy.autonomous_core import autonomy_core
        await autonomy_core.initialize()
        logger.info("Autonomous persistent background task scheduler and Autonomy Core online.")
    except Exception as e:
        logger.error(f"Failed to start background scheduler/Autonomy Core: {e}")

    logger.info(f"MATRIX Server online at http://{settings.host}:{settings.port}")
    yield
    try:
        from voice.mic_listener import mic_listener
        mic_listener.stop()
    except Exception:
        pass
    
    try:
        from automation.scheduler.engine import background_scheduler
        await background_scheduler.stop()
    except Exception:
        pass
    logger.info("MATRIX Server shutting down cleanly...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="JARVIS-inspired Personal AI Ecosystem Core API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global timing and request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()
    logger.debug(f"[{request_id}] {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time"] = f"{process_time_ms}ms"
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(f"[{request_id}] Unhandled error processing {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "request_id": request_id,
                "detail": str(exc) if settings.debug else "An unexpected error occurred."
            }
        )


# Include REST API Routers under /api/v1 prefix
app.include_router(health.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(capabilities.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(vision.router, prefix="/api/v1")
app.include_router(repositories.router, prefix="/api/v1")
app.include_router(automation.router, prefix="/api/v1")
app.include_router(automation.automation_router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(developer.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(airtouch.router, prefix="/api/v1")
app.include_router(telephony.router, prefix="/api/v1")
app.include_router(briefing.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")

# Direct alias for /api/v1/telemetry
@app.get("/api/v1/telemetry", tags=["System Telemetry"])
async def get_telemetry_alias():
    """Direct alias routing /api/v1/telemetry to system telemetry."""
    return await system.get_system_telemetry()

# Mount React UI static assets if built
from pathlib import Path
from fastapi.staticfiles import StaticFiles

ui_dist_dir = Path(__file__).resolve().parent.parent / "desktop" / "ui" / "dist"
if ui_dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(ui_dist_dir / "assets")), name="static_assets")

    @app.get("/", tags=["UI"])
    async def serve_ui():
        from fastapi.responses import FileResponse
        return FileResponse(str(ui_dist_dir / "index.html"))

    @app.get("/{full_path:path}", tags=["UI"], include_in_schema=False)
    async def serve_spa_catchall(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path.startswith("assets/"):
            return JSONResponse(status_code=404, content={"error": "Not Found"})
        from fastapi.responses import FileResponse
        return FileResponse(str(ui_dist_dir / "index.html"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint verifying MATRIX Core is active."""
        return {
            "name": settings.app_name,
            "version": settings.version,
            "status": "OPERATIONAL",
            "system": "JARVIS-inspired Personal AI Ecosystem",
            "docs": "/docs",
            "health": "/api/v1/health"
        }


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Bidirectional real-time event socket for UI command center and mobile companions.

    Local clients are trusted; remote clients must present a valid MATRIX API token or a
    paired device token. Without a token the socket is closed instead of being granted
    full broker access (previously any client could connect anonymously).
    """
    client_host = websocket.client.host if websocket.client else None
    token = websocket.query_params.get("token")
    authorized = is_trusted_client(client_host)

    if not authorized and token:
        if matches_api_token(token):
            authorized = True
        else:
            from core.device_auth import validate_token_raw
            from database.session import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                authorized = (await validate_token_raw(token, session)) is not None

    if not authorized:
        logger.warning("Rejected unauthenticated WebSocket client from %s", client_host)
        await websocket.close(code=4001, reason="Unauthorized: provide a valid token")
        return

    await ws_manager.connect(websocket)
    from voice.conversation.manager import hands_free_manager, ConversationMode
    import json
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WS message: {data}")
            try:
                msg = json.loads(data)
                mtype = msg.get("type", "")
                if mtype == "voice_interrupt":
                    await hands_free_manager.interrupt()
                elif mtype == "set_mode":
                    mode_val = msg.get("mode")
                    if mode_val in [m.value for m in ConversationMode]:
                        hands_free_manager.set_mode(ConversationMode(mode_val))
                elif mtype == "trigger_listen":
                    await hands_free_manager.handle_wake_word_activation("manual")
            except Exception:
                pass
            # Echo or dispatch user events
            await websocket.send_json({
                "type": "ack",
                "received": data
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
