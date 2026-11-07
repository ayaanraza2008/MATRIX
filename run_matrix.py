"""MATRIX Launcher Script.
Launches the FastAPI backend and provides live links to the Command Interface.
"""
import uvicorn
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("launcher")

if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("   MATRIX — Personal AI Ecosystem (PC + Android)  ")
    logger.info(f"   Storage Root: {settings.data_dir}")
    logger.info(f"   Web HUD:      http://{settings.host}:{settings.port}/")
    logger.info(f"   API Docs:     http://{settings.host}:{settings.port}/docs")
    logger.info("==================================================")

    uvicorn.run(
        "api.server:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
