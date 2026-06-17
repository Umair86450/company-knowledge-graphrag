from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: int | None = None


class ChatResponse(BaseModel):
    session_id: int
    reply: str


class Message(BaseModel):
    role: str
    content: str
