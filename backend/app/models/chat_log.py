import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    question = Column(Text, nullable=False)
    answer = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # V6 Extensions
    topic_id = Column(Integer, ForeignKey("chat_topics.id"))
    latency_ms = Column(Integer)
    status = Column(String(20), default="success")

    # Relationship to cleanly map topic_id -> ChatTopic model
    topic = relationship("ChatTopic")