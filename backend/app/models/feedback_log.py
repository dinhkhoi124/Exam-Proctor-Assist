import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_logs.id", ondelete="SET NULL"), nullable=True)
    rating = Column(String(50), nullable=False)
    comment = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks")
    chat_log = relationship("ChatLog", back_populates="feedbacks")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="resolved_feedbacks")
