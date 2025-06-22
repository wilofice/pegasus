"""Webhook router receiving pipeline notifications."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from ..core import proactive_engine

router = APIRouter(prefix="/webhook", tags=["webhook"])


class WebhookPayload(BaseModel):
    file_path: str


def _auth(x_token: str | None = Header(default=None)) -> None:
    if x_token != "pipeline-secret":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/")
async def webhook(payload: WebhookPayload, _: None = Depends(_auth)) -> dict:
    """Process notifications from the data pipeline."""
    proactive_engine.process_notification(payload.dict())
    return {"status": "received"}
