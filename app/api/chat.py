import logging

from fastapi import APIRouter, HTTPException

from app.models.db import add_message, create_session, get_messages, get_or_create_user
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.services.claude_service import ClaudeError, chat

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def post_chat(request: ChatRequest) -> ChatResponse:
    user_id = get_or_create_user(request.username)
    session_id = request.session_id or create_session(user_id)

    add_message(session_id, "user", request.message)

    try:
        reply = chat(session_id, request.message)
    except ClaudeError as exc:
        logger.error("Claude chat failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=502, detail="Claude is unavailable, please try again.")

    add_message(session_id, "assistant", reply)
    return ChatResponse(session_id=session_id, reply=reply)


@router.get("/history/{session_id}", response_model=list[Message])
def get_history(session_id: int) -> list[Message]:
    return get_messages(session_id)
