from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.db.deps import get_db
from app.models.user import User
from app.models.chat_log import ChatLog
from app.models.chat_topic import ChatTopic
from app.services.auth_service import get_current_user_from_token, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])
# =========================
# ADMIN STATS
# =========================
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    # check admin
    require_admin(current_user)

    # TOTAL USERS
    total_users = db.query(func.count(User.id)).filter(User.role == 'user').scalar()

    # TOTAL QUESTIONS
    total_questions = db.query(func.count(ChatLog.id)).join(User).filter(User.role == 'user').scalar()

    # ONLINE USERS (5 phút)
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

    online_users = db.query(func.count(User.id)).filter(
        User.role == 'user',
        User.last_active != None,
        User.last_active >= five_minutes_ago
    ).scalar()

    # QUESTIONS PER USER
    users_data = (
        db.query(
            User.username,
            User.email,
            User.id,
            func.count(ChatLog.id).label("question_count")
        )
        .outerjoin(ChatLog, ChatLog.user_id == User.id)
        .filter(User.role == 'user')
        .group_by(User.id)
        .all()
    )

    result = [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "question_count": u.question_count
        }
        for u in users_data
    ]

    return {
        "total_users": total_users,
        "total_questions": total_questions,
        "online_users": online_users,
        "users": result
    }

@router.get("/metrics")
def get_metrics(
    range: str = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    if range == "day":
        group = func.date(ChatLog.created_at)
    elif range == "week":
        group = func.date_trunc('week', ChatLog.created_at)
    elif range == "month":
        group = func.date_trunc('month', ChatLog.created_at)
    else:
        raise HTTPException(status_code=400, detail="Invalid range")

    data = (
        db.query(
            group.label("time"),
            func.count(ChatLog.id).label("questions"),
            func.count(func.distinct(ChatLog.user_id)).label("users")
        )
        .group_by(group)
        .order_by(group)
        .all()
    )

    return [
        {
            "time": str(row.time),
            "questions": row.questions,
            "users": row.users
        }
        for row in data
    ]

@router.get("/top-topics")
def get_top_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    data = (
        db.query(
            ChatTopic.name.label("topic"),
            func.count(ChatLog.id).label("count")
        )
        .join(ChatLog.topic)
        .group_by(ChatTopic.name)
        .order_by(func.count(ChatLog.id).desc())
        .all()
    )

    return [{"topic": t.topic, "count": t.count} for t in data]

@router.get("/user/{user_id}/chats")
def get_user_chats(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    chats = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == user_id)
        .order_by(ChatLog.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "question": c.question,
            "answer": c.answer[:200] if c.answer else "",  # preview
            "topic": c.topic.name if c.topic else "General",
            "created_at": c.created_at
        }
        for c in chats
    ]