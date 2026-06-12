from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class FeedbackCreate(BaseModel):
    chat_id: UUID
    rating: str  # "like" or "dislike"
    comment: Optional[str] = None


class FeedbackUserDetail(BaseModel):
    username: str
    email: str

    class Config:
        orm_mode = True
        from_attributes = True


class FeedbackChatDetail(BaseModel):
    question: str
    answer: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class FeedbackResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    chat_id: Optional[UUID]
    rating: str
    comment: Optional[str]
    is_resolved: bool
    is_deleted: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None

    # Relationship joins
    user: Optional[FeedbackUserDetail] = None
    chat_log: Optional[FeedbackChatDetail] = None
    resolver: Optional[FeedbackUserDetail] = None

    class Config:
        orm_mode = True
        from_attributes = True


class FeedbackResolve(BaseModel):
    is_resolved: bool
