import uuid
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base

class EmailSetting(Base):
    __tablename__ = "email_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    smtp_server = Column(String(255), nullable=False)
    smtp_port = Column(Integer, nullable=False)
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=False)
    use_tls = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
