"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

from api import chat_router, webhook_router, audio_router, game_router, chat_router_v2, llm_router
from routers import context, plugins
from core.config import settings
from core.database import create_tables
from middleware import SelectiveLoggingMiddleware, RequestLoggingConfig
# Import all models to ensure they're registered
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory
import logging
logger = logging.getLogger(__name__)

logger.info("Starting Pegasus Brain with settings...\n" + str(settings))


async def run_migrations():
    """Run database migrations on startup."""
    try:
        import subprocess
        import os
        
        # Change to backend directory
        backend_dir = Path(__file__).parent
        original_cwd = os.getcwd()
        os.chdir(backend_dir)
        
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.error(f"Migration failed: {result.stderr}")
            # Fallback to direct table creation
            logger.info("Falling back to direct table creation...")
            await create_tables()
        
    except Exception as e:
        logger.warning(f"Could not run migrations: {e}")
        logger.info("Falling back to direct table creation...")
        await create_tables()
    finally:
        os.chdir(original_cwd)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    #logger.info("Initializing database...")
    
    #if settings.auto_migrate_on_startup:
        #logger.info("Auto-migration enabled - running migrations...")
        # await run_migrations()
    #else:
        #logger.info("Auto-migration disabled - creating tables only...")
        # await create_tables()
    
    #logger.info("Database initialization completed!")
    
    yield
    
    # Shutdown (if needed)
    pass


app = FastAPI(title="Pegasus Backend", lifespan=lifespan)

# Add request/response logging middleware
if settings.enable_request_logging:
    logging_config = RequestLoggingConfig(
        log_dir=settings.log_directory,
        max_body_size=settings.log_max_body_size,
        log_binary_content=settings.log_binary_content,
        excluded_paths=settings.log_excluded_paths,
        excluded_methods=settings.log_excluded_methods
    )
    app.add_middleware(SelectiveLoggingMiddleware, config=logging_config)

app.include_router(chat_router.router)
app.include_router(webhook_router.router)
app.include_router(audio_router.router)
app.include_router(game_router.router)
app.include_router(context.router)
app.include_router(plugins.router)
app.include_router(chat_router_v2.router)
app.include_router(llm_router.router)


@app.get("/health")
def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - manual launch
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
