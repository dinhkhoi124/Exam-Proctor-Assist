import uuid
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text, text
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

    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    delete_reason = Column(Text, nullable=True)
    purged_at = Column(DateTime(timezone=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_verified = Column(Boolean, default=False)
    verification_token = Column(Text)
    verification_expiry = Column(DateTime(timezone=True))

    reset_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    role = Column(String(20), default="user")
    last_active = Column(DateTime(timezone=True))
    session_version = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Relationships
    feedbacks = relationship("FeedbackLog", back_populates="user", foreign_keys="[FeedbackLog.user_id]")
    resolved_feedbacks = relationship("FeedbackLog", back_populates="resolver", foreign_keys="[FeedbackLog.resolved_by]")
