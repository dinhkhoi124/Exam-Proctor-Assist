from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta

from app.db.deps import get_db
from app.models.user import User
from app.models.chat_log import ChatLog
from app.models.chat_topic import ChatTopic
from app.models.chat_session import ChatSession
from app.services.auth_service import get_current_user_from_token, require_manager_or_admin,require_admin
from app.schemas.auth import UpdateRoleRequest

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
    require_manager_or_admin(current_user)

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

    # FEEDBACK STATISTICS
    from app.models.feedback_log import FeedbackLog
    total_feedbacks = db.query(func.count(FeedbackLog.id)).filter(FeedbackLog.is_deleted == False).scalar()
    
    feedback_rows = db.query(
        FeedbackLog.rating,
        func.count(FeedbackLog.id)
    ).filter(
        FeedbackLog.is_deleted == False
    ).group_by(
        FeedbackLog.rating
    ).all()
    
    feedback_distribution = {"like": 0, "dislike": 0}
    for rating_val, count_val in feedback_rows:
        if rating_val:
            feedback_distribution[rating_val] = count_val

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
        "users": result,
        "total_feedbacks": total_feedbacks,
        "feedback_distribution": feedback_distribution
    }

@router.get("/metrics")
def get_metrics(
    range: str = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_manager_or_admin(current_user)

    if range == "day":
        group = func.date(ChatLog.created_at)
    elif range == "week":
        group = func.date_trunc('week', ChatLog.created_at)
    elif range == "month":
        group = func.date_trunc('month', ChatLog.created_at)
    elif range == "year":
        group = func.date_trunc('year', ChatLog.created_at)
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
    require_manager_or_admin(current_user)

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
    require_manager_or_admin(current_user)

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

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role"
        )
    user.role = request.role

    db.commit()
    db.refresh(user)

    return {
        "message": "Role updated successfully",
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role
    }

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    users_with_counts = (
        db.query(
            User.id,
            User.username,
            User.email,
            User.role,
            User.is_active,
            User.created_at,
            User.last_active,
            func.max(ChatLog.created_at).label("last_chat_time"),
            func.count(ChatLog.id).label("question_count")
        )
        .outerjoin(ChatLog, ChatLog.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_active": u.last_chat_time or u.last_active,
            "question_count": u.question_count
        }
        for u in users_with_counts
    ]


@router.get("/chat-logs")
def get_all_chat_logs(
    user_id: str = None,
    query: str = None,
    topic: str = None,
    range: str = "all",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_manager_or_admin(current_user)
    
    # Eager-load relations to optimize queries and avoid N+1 issues
    db_query = db.query(ChatLog, User).outerjoin(User, ChatLog.user_id == User.id).options(
        joinedload(ChatLog.topic),
        joinedload(ChatLog.session)
    )
    
    if user_id and user_id != "all":
        db_query = db_query.filter(ChatLog.user_id == user_id)
        
    if topic and topic != "all":
        if topic == "General Guidance":
            db_query = db_query.outerjoin(ChatTopic, ChatLog.topic_id == ChatTopic.id).filter(
                (ChatLog.topic_id == None) | (ChatTopic.name == "General Guidance")
            )
        else:
            db_query = db_query.join(ChatTopic, ChatLog.topic_id == ChatTopic.id).filter(ChatTopic.name == topic)
            
    if range and range != "all":
        now_utc = datetime.utcnow()
        if range == "day":
            start_date = datetime(now_utc.year, now_utc.month, now_utc.day)
            db_query = db_query.filter(ChatLog.created_at >= start_date)
        elif range == "month":
            start_date = datetime(now_utc.year, now_utc.month, 1)
            db_query = db_query.filter(ChatLog.created_at >= start_date)
        elif range == "year":
            start_date = datetime(now_utc.year, 1, 1)
            db_query = db_query.filter(ChatLog.created_at >= start_date)
            
    if query:
        search_pattern = f"%{query}%"
        db_query = db_query.filter(
            (ChatLog.question.ilike(search_pattern)) | 
            (ChatLog.answer.ilike(search_pattern))
        )
        
    total = db_query.count()
    
    if sort_order == "asc":
        db_query = db_query.order_by(ChatLog.created_at.asc())
    else:
        db_query = db_query.order_by(ChatLog.created_at.desc())
        
    offset = (page - 1) * limit
    logs = db_query.offset(offset).limit(limit).all()
    has_next = offset + len(logs) < total
    
    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id),
            "username": user.username if user else "Unknown",
            "email": user.email if user else "Unknown",
            "question": log.question,
            "answer": log.answer,
            "topic": log.topic.name if log.topic else "General Guidance",
            "created_at": log.created_at,
            "session_title": log.session.title if log.session else None
        }
        for log, user in logs
    ]
    
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "has_next": has_next
    }