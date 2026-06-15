from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class ChatSessionUpdate(BaseModel):
    title: str

class ChatHistoryMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
