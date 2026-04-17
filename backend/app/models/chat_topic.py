from sqlalchemy import Column, Integer, String
from app.db.session import Base

class ChatTopic(Base):
    __tablename__ = "chat_topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)