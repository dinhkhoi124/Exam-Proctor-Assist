import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)

    full_name = Column(String(100))
    avatar_url = Column(Text)

    is_active = Column(Boolean, default=True)

    is_verified = Column(Boolean, default=False)
    verification_token = Column(Text)
    verification_expiry = Column(DateTime)

    reset_token = Column(Text)
    token_expiry = Column(DateTime)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    role = Column(String(20), default="user")
    last_active = Column(DateTime)

    # Relationships
    feedbacks = relationship("FeedbackLog", back_populates="user", foreign_keys="[FeedbackLog.user_id]", cascade="all, delete-orphan")
    resolved_feedbacks = relationship("FeedbackLog", back_populates="resolver", foreign_keys="[FeedbackLog.resolved_by]")