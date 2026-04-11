from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.db.deps import get_db
from app.models.user import User
from app.models.chat_log import ChatLog
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

    # =========================
    # TOTAL USERS
    # =========================
    total_users = db.query(func.count(User.id)).filter(User.role == 'user').scalar()

    # =========================
    # TOTAL QUESTIONS
    # =========================
    total_questions = db.query(func.count(ChatLog.id)).join(User).filter(User.role == 'user').scalar()

    # =========================
    # ONLINE USERS (5 phút)
    # =========================
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

    online_users = db.query(func.count(User.id)).filter(
        User.role == 'user',
        User.last_active != None,
        User.last_active >= five_minutes_ago
    ).scalar()

    # =========================
    # QUESTIONS PER USER
    # =========================
    users_data = (
        db.query(
            User.username,
            User.email,
            func.count(ChatLog.id).label("question_count")
        )
        .outerjoin(ChatLog, ChatLog.user_id == User.id)
        .filter(User.role == 'user')
        .group_by(User.id)
        .all()
    )

    result = [
        {
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