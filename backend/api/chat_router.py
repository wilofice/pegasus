"""Chat router handling user messages."""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel

from ..core import orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


def _auth(authorization: str | None = Header(default=None)) -> None:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, _: None = Depends(_auth)) -> ChatResponse:
    """Handle chat messages from the frontend."""
    reply = orchestrator.handle_chat(request.message)
    return ChatResponse(response=reply)
