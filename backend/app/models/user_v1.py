

import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)

    full_name = Column(String(100))
    avatar_url = Column(Text)

    is_active = Column(Boolean, default=False)  # Trạng thái kích hoạt
    activation_token = Column(String, nullable=True)  # Token kích hoạt
    token_expiry = Column(DateTime, nullable=True)  # Hạn sử dụng token

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
