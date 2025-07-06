"""FastAPI application entry point."""
from fastapi import FastAPI

from api import chat_router, webhook_router, audio_router, game_router, chat_router_v2, llm_router
from routers import context, plugins
from core.config import settings
from middleware import SelectiveLoggingMiddleware, RequestLoggingConfig

app = FastAPI(title="Pegasus Backend")

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
