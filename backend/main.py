"""FastAPI application entry point."""
from fastapi import FastAPI

from api import chat_router, webhook_router, audio_router

app = FastAPI(title="Pegasus Backend")

app.include_router(chat_router.router)
app.include_router(webhook_router.router)
app.include_router(audio_router.router)


@app.get("/health")
def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - manual launch
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
