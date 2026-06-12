from sqlalchemy.orm import Session
from app.models.chat_log import ChatLog
from app.models.user_activity import UserActivityLog
from app.models.chat_topic import ChatTopic


def log_user_activity(db: Session, user_id, activity_type: str):
    log = UserActivityLog(
        user_id=user_id,
        activity_type=activity_type
    )
    db.add(log)
    db.commit()

def get_topic_id(db: Session, topic_name: str):
    topic = db.query(ChatTopic).filter(ChatTopic.name == topic_name).first()
    return topic.id if topic else None


def save_chat_log(
    db: Session,
    user_id,
    question,
    answer,
    topic_name,
    latency,
    session_id=None
):
    topic_id = get_topic_id(db, topic_name)

    chat = ChatLog(
        user_id=user_id,
        question=question,
        answer=answer,
        topic_id=topic_id,   
        latency_ms=latency,
        status="success",
        session_id=session_id
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat