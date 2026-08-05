import uuid
from sqlalchemy import Boolean, Column, Text, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    question = Column(Text, nullable=False)
    answer = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deletion_batch_id = Column(UUID(as_uuid=True), nullable=True)

    # V6 Extensions
    topic_id = Column(Integer, ForeignKey("chat_topics.id"))
    latency_ms = Column(Integer)
    status = Column(String(20), default="success")
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    topic = relationship("ChatTopic")
    session = relationship("ChatSession", back_populates="logs")
    feedbacks = relationship("FeedbackLog", back_populates="chat_log")