from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
import secrets
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.db.deps import get_db
from app.models.user import User
from app.models.chat_log import ChatLog
from app.models.chat_topic import ChatTopic
from app.models.chat_session import ChatSession
from app.models.rag_document import RagDocument
from app.services.auth_service import get_current_user_from_token, hash_password, require_manager_or_admin,require_admin
from app.core.websocket import manager
from app.services.logging_service import log_user_activity

from app.schemas.auth import UpdateRoleRequest

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
VALID_LOG_RANGES = {"day", "week", "month", "year"}


def _vn_time_bounds(range_name: str) -> tuple[datetime, datetime]:
    now_vn = datetime.now(VN_TZ)
    if range_name == "day":
        start = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif range_name == "week":
        start = (now_vn - timedelta(days=now_vn.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=7)
    elif range_name == "month":
        start = now_vn.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    elif range_name == "year":
        start = now_vn.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
    else:
        raise HTTPException(status_code=400, detail="Khoảng thời gian không hợp lệ")

    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


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
    total_users = db.query(func.count(User.id)).filter(
        User.role == 'user',
        User.is_deleted.is_(False),
    ).scalar()

    # TOTAL QUESTIONS
    total_questions = db.query(func.count(ChatLog.id)).join(
        User, ChatLog.user_id == User.id
    ).filter(
        User.role == 'user',
        ChatLog.is_deleted.is_(False),
    ).scalar()

    # ONLINE USERS (5 phút)
    five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

    online_users = db.query(func.count(User.id)).filter(
        User.is_deleted.is_(False),
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

    document_status_rows = (
        db.query(RagDocument.status, func.count(RagDocument.id))
        .filter(RagDocument.status != "deleted")
        .group_by(RagDocument.status)
        .all()
    )
    document_statuses = {"ready": 0, "indexing": 0, "failed": 0}
    for document_status, count in document_status_rows:
        if document_status in document_statuses:
            document_statuses[document_status] = count
    total_documents = sum(document_statuses.values())

    # QUESTIONS PER USER
    users_data = (
        db.query(
            User.username,
            User.email,
            User.id,
            func.count(ChatLog.id).label("question_count")
        )
        .outerjoin(ChatLog, and_(
            ChatLog.user_id == User.id,
            ChatLog.is_deleted.is_(False),
        ))
        .filter(User.role == 'user', User.is_deleted.is_(False))
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
        "feedback_distribution": feedback_distribution,
        "total_documents": total_documents,
        "document_statuses": document_statuses,
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
        .filter(ChatLog.is_deleted.is_(False))
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
        .filter(ChatLog.is_deleted.is_(False))
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
        .filter(ChatLog.user_id == user_id, ChatLog.is_deleted.is_(False))
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

    if user.is_deleted:
        raise HTTPException(status_code=400, detail="Không thể đổi vai trò tài khoản đang chờ xóa")

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
            User.is_deleted,
            User.deleted_at,
            User.purged_at,
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
        .outerjoin(ChatLog, and_(
            ChatLog.user_id == User.id,
            ChatLog.is_deleted.is_(False),
        ))
        .filter(User.purged_at.is_(None))
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
            "question_count": u.question_count,
            "is_deleted": u.is_deleted,
            "deleted_at": u.deleted_at,
            "purged_at": u.purged_at,
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
    ).filter(ChatLog.is_deleted.is_(False))
    
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
        if range not in VALID_LOG_RANGES:
            raise HTTPException(status_code=400, detail="Khoảng thời gian không hợp lệ")
        start_date, end_date = _vn_time_bounds(range)
        db_query = db_query.filter(ChatLog.created_at >= start_date, ChatLog.created_at < end_date)
            
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
            "username": user.username if user and not user.purged_at else "Tài khoản đã xóa",
            "email": user.email if user and not user.purged_at else "",
            "question": log.question,
            "answer": log.answer,
            "topic": log.topic.name if log.topic else "General Guidance",
            "created_at": log.created_at,
            "session_title": log.session.title if log.session else None,
            "session_id": str(log.session_id) if log.session_id else None,
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



@router.get("/chat-sessions/{session_id}/logs")
def get_admin_chat_session_logs(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_manager_or_admin(current_user)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.is_deleted.is_(False),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat")

    logs = db.query(ChatLog).options(
        joinedload(ChatLog.topic)
    ).filter(
        ChatLog.session_id == session_id,
        ChatLog.is_deleted.is_(False),
    ).order_by(ChatLog.created_at.asc()).all()

    return {
        "session_id": str(session.id),
        "session_title": session.title,
        "items": [
            {
                "id": str(log.id),
                "question": log.question,
                "answer": log.answer,
                "topic": log.topic.name if log.topic else "General Guidance",
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }

def _parse_uuid_values(values, field_name: str) -> list[UUID]:
    if not isinstance(values, list) or not values:
        raise HTTPException(status_code=400, detail=f"{field_name} không được để trống")
    if len(values) > 1000:
        raise HTTPException(status_code=400, detail="Mỗi lần chỉ được xử lý tối đa 1000 mục")
    try:
        return [UUID(str(value)) for value in values]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} chứa ID không hợp lệ")


def _chat_log_delete_query(db: Session, payload: dict):
    mode = payload.get("mode")
    query = db.query(ChatLog).filter(ChatLog.is_deleted.is_(False))

    if mode == "selected":
        return query.filter(ChatLog.id.in_(_parse_uuid_values(payload.get("log_ids"), "log_ids")))
    if mode == "session":
        session_ids = _parse_uuid_values(payload.get("session_ids"), "session_ids")
        return query.filter(ChatLog.session_id.in_(session_ids))
    if mode == "range":
        range_name = payload.get("range")
        if range_name not in VALID_LOG_RANGES:
            raise HTTPException(status_code=400, detail="Khoảng thời gian không hợp lệ")
        try:
            user_id = UUID(str(payload.get("user_id")))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Phải chọn một tài khoản hợp lệ")
        start_at, end_at = _vn_time_bounds(range_name)
        return query.filter(
            ChatLog.user_id == user_id,
            ChatLog.created_at >= start_at,
            ChatLog.created_at < end_at,
        )

    raise HTTPException(status_code=400, detail="Chế độ xóa không hợp lệ")


def _chat_log_delete_counts(query) -> tuple[int, int]:
    log_count = query.count()
    session_count = query.filter(ChatLog.session_id.is_not(None)).with_entities(
        func.count(func.distinct(ChatLog.session_id))
    ).scalar() or 0
    return log_count, session_count


def _soft_delete_empty_sessions(
    db: Session,
    session_ids: set[UUID],
    deleted_at: datetime,
    deleted_by: UUID,
    deletion_batch_id: UUID,
) -> int:
    deleted_sessions = 0
    for session_id in session_ids:
        has_active_log = db.query(ChatLog.id).filter(
            ChatLog.session_id == session_id,
            ChatLog.is_deleted.is_(False),
        ).first()
        if not has_active_log:
            deleted_sessions += db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.is_deleted.is_(False),
            ).update(
                {
                    ChatSession.is_deleted: True,
                    ChatSession.deleted_at: deleted_at,
                    ChatSession.deleted_by: deleted_by,
                    ChatSession.deletion_batch_id: deletion_batch_id,
                },
                synchronize_session=False,
            )
    return deleted_sessions


@router.post("/chat-logs/delete-preview")
def preview_chat_log_delete(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    log_count, session_count = _chat_log_delete_counts(_chat_log_delete_query(db, payload))
    return {"log_count": log_count, "session_count": session_count}


@router.post("/chat-logs/bulk-delete")
async def bulk_delete_chat_logs(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    query = _chat_log_delete_query(db, payload)
    rows = query.with_entities(ChatLog.id, ChatLog.session_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhật ký phù hợp để xóa")

    now_utc = datetime.now(timezone.utc)
    deletion_batch_id = uuid4()
    log_ids = [row.id for row in rows]
    session_ids = {row.session_id for row in rows if row.session_id is not None}
    deleted_logs = db.query(ChatLog).filter(ChatLog.id.in_(log_ids)).update(
        {
            ChatLog.is_deleted: True,
            ChatLog.deleted_at: now_utc,
            ChatLog.deleted_by: current_user.id,
            ChatLog.deletion_batch_id: deletion_batch_id,
        },
        synchronize_session=False,
    )
    deleted_sessions = _soft_delete_empty_sessions(
        db,
        session_ids,
        now_utc,
        current_user.id,
        deletion_batch_id,
    )
    db.commit()

    log_user_activity(
        db,
        current_user.id,
        "admin_delete_logs",
        {
            "mode": payload.get("mode"),
            "deleted_logs": deleted_logs,
            "deleted_sessions": deleted_sessions,
            "deletion_batch_id": str(deletion_batch_id),
        },
    )
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"deleted_logs": deleted_logs, "deleted_sessions": deleted_sessions}


def _get_manageable_user(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id, User.purged_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    return user


def _protect_admin_account(db: Session, target: User, current_user: User):
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Bạn không thể thực hiện thao tác này với chính mình")
    if target.role == "admin" and target.is_active:
        active_admins = db.query(func.count(User.id)).filter(
            User.role == "admin",
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        ).scalar() or 0
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa admin cuối cùng")


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    if not isinstance(payload.get("is_active"), bool):
        raise HTTPException(status_code=400, detail="is_active phải là boolean")

    user = _get_manageable_user(db, user_id)
    if user.is_deleted:
        raise HTTPException(status_code=400, detail="Không thể khóa/mở khóa tài khoản đang chờ xóa")
    if not payload["is_active"]:
        _protect_admin_account(db, user, current_user)

    user.is_active = payload["is_active"]
    user.locked_at = None if user.is_active else datetime.now(timezone.utc)
    user.locked_by = None if user.is_active else current_user.id
    if not user.is_active:
        user.last_active = None
    db.commit()

    log_user_activity(
        db,
        current_user.id,
        "admin_unlock_user" if user.is_active else "admin_lock_user",
        {"target_user_id": str(user.id)},
    )
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"message": "Đã mở khóa tài khoản" if user.is_active else "Đã khóa tài khoản"}


@router.delete("/users/{user_id}")
async def soft_delete_user(
    user_id: UUID,
    reason: str | None = Query(default=None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    user = _get_manageable_user(db, user_id)
    if user.is_deleted:
        raise HTTPException(status_code=400, detail="Tài khoản đã ở trạng thái chờ xóa")
    _protect_admin_account(db, user, current_user)

    user.is_active = False
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by = current_user.id
    user.delete_reason = reason
    user.locked_at = user.deleted_at
    user.locked_by = current_user.id
    user.last_active = None
    user.reset_token = None
    user.token_expiry = None
    user.verification_token = None
    user.verification_expiry = None
    db.commit()

    log_user_activity(db, current_user.id, "admin_delete_user", {"target_user_id": str(user.id)})
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"message": "Tài khoản sẽ được giữ 30 ngày trước khi xóa vĩnh viễn thông tin cá nhân"}


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    user = _get_manageable_user(db, user_id)
    if not user.is_deleted:
        raise HTTPException(status_code=400, detail="Tài khoản không ở trạng thái chờ xóa")

    user.is_deleted = False
    user.is_active = True
    user.deleted_at = None
    user.deleted_by = None
    user.delete_reason = None
    user.locked_at = None
    user.locked_by = None
    db.commit()

    log_user_activity(db, current_user.id, "admin_restore_user", {"target_user_id": str(user.id)})
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"message": "Đã khôi phục tài khoản"}


def _anonymize_user(user: User, purged_at: datetime) -> None:
    tombstone = user.id.hex
    user.username = f"deleted_{tombstone}"
    user.email = f"deleted_{tombstone}@deleted.local"
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.full_name = None
    user.avatar_url = None
    user.reset_token = None
    user.token_expiry = None
    user.verification_token = None
    user.verification_expiry = None
    user.delete_reason = None
    user.role = "user"
    user.purged_at = purged_at


def purge_expired_users(db: Session, retention_days: int = 30) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    users = db.query(User).filter(
        User.is_deleted.is_(True),
        User.purged_at.is_(None),
        User.deleted_at <= cutoff,
    ).all()

    now_utc = datetime.now(timezone.utc)
    for user in users:
        _anonymize_user(user, now_utc)
    db.commit()
    return len(users)


@router.post("/users/purge-expired")
def purge_expired_users_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    count = purge_expired_users(db)
    log_user_activity(db, current_user.id, "admin_purge_users", {"purged_users": count})
    return {"purged_users": count}


TRASH_RETENTION_DAYS = 30
PERMANENT_DELETE_CONFIRMATION = "XOA VINH VIEN"


def _chat_trash_batch_ids(db: Session) -> set[UUID]:
    log_batches = db.query(ChatLog.deletion_batch_id).filter(
        ChatLog.is_deleted.is_(True),
        ChatLog.deletion_batch_id.is_not(None),
    ).distinct().all()
    session_batches = db.query(ChatSession.deletion_batch_id).filter(
        ChatSession.is_deleted.is_(True),
        ChatSession.deletion_batch_id.is_not(None),
    ).distinct().all()
    return {row[0] for row in log_batches + session_batches if row[0] is not None}


def _hard_delete_chat_batch(db: Session, batch_id: UUID) -> tuple[int, int]:
    session_ids = {
        row[0]
        for row in db.query(ChatLog.session_id).filter(
            ChatLog.deletion_batch_id == batch_id,
            ChatLog.session_id.is_not(None),
        ).distinct().all()
    }
    session_ids.update(
        row[0]
        for row in db.query(ChatSession.id).filter(
            ChatSession.deletion_batch_id == batch_id,
            ChatSession.is_deleted.is_(True),
        ).all()
    )

    deleted_logs = db.query(ChatLog).filter(
        ChatLog.deletion_batch_id == batch_id,
        ChatLog.is_deleted.is_(True),
    ).delete(synchronize_session=False)

    deleted_sessions = 0
    for session_id in session_ids:
        has_remaining_logs = db.query(ChatLog.id).filter(
            ChatLog.session_id == session_id
        ).first()
        if not has_remaining_logs:
            deleted_sessions += db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.is_deleted.is_(True),
            ).delete(synchronize_session=False)
    return deleted_logs, deleted_sessions


@router.get("/trash")
def get_trash(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    users = db.query(User).filter(
        User.is_deleted.is_(True),
        User.purged_at.is_(None),
    ).order_by(User.deleted_at.desc()).all()

    actor_ids = {user.deleted_by for user in users if user.deleted_by}
    actor_names = dict(
        db.query(User.id, User.username).filter(User.id.in_(actor_ids)).all()
    ) if actor_ids else {}
    user_items = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "delete_reason": user.delete_reason,
            "deleted_at": user.deleted_at,
            "deleted_by": actor_names.get(user.deleted_by),
            "expires_at": user.deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
            if user.deleted_at else None,
        }
        for user in users
    ]

    batch_items = []
    for batch_id in _chat_trash_batch_ids(db):
        logs = db.query(ChatLog).filter(
            ChatLog.deletion_batch_id == batch_id,
            ChatLog.is_deleted.is_(True),
        )
        sessions = db.query(ChatSession).filter(
            ChatSession.deletion_batch_id == batch_id,
            ChatSession.is_deleted.is_(True),
        )
        first_log = logs.order_by(ChatLog.deleted_at.asc()).first()
        first_session = sessions.order_by(ChatSession.deleted_at.asc()).first()
        deleted_at = (
            first_log.deleted_at if first_log else
            first_session.deleted_at if first_session else None
        )
        deleted_by_id = (
            first_log.deleted_by if first_log else
            first_session.deleted_by if first_session else None
        )
        owner_id = (
            first_session.user_id if first_session else
            first_log.user_id if first_log else None
        )
        owner = db.query(User).filter(User.id == owner_id).first() if owner_id else None
        actor = db.query(User).filter(User.id == deleted_by_id).first() if deleted_by_id else None
        deletion_source = (
            "self_service" if deleted_by_id and deleted_by_id == owner_id else
            "admin" if deleted_by_id else
            "unknown"
        )
        title = first_session.title if first_session else (
            first_log.question[:120] if first_log else "Nhật ký trò chuyện"
        )
        batch_items.append(
            {
                "batch_id": batch_id,
                "title": title,
                "log_count": logs.count(),
                "session_count": sessions.count(),
                "deleted_at": deleted_at,
                "deleted_by": (
                    actor.username if actor and not actor.purged_at else
                    "Tài khoản đã xóa" if actor else None
                ),
                "deletion_source": deletion_source,
                "owner_user_id": str(owner_id) if owner_id else None,
                "owner_username": (
                    owner.username if owner and not owner.purged_at else
                    "Tài khoản đã xóa" if owner else None
                ),
                "owner_email": owner.email if owner and not owner.purged_at else "",
                "expires_at": deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
                if deleted_at else None,
            }
        )
    batch_items.sort(
        key=lambda item: item["deleted_at"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return {"users": user_items, "chat_batches": batch_items}


@router.post("/trash/chats/{batch_id}/restore")
async def restore_chat_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    session_ids = {
        row[0]
        for row in db.query(ChatLog.session_id).filter(
            ChatLog.deletion_batch_id == batch_id,
            ChatLog.is_deleted.is_(True),
            ChatLog.session_id.is_not(None),
        ).distinct().all()
    }
    restored_logs = db.query(ChatLog).filter(
        ChatLog.deletion_batch_id == batch_id,
        ChatLog.is_deleted.is_(True),
    ).update(
        {
            ChatLog.is_deleted: False,
            ChatLog.deleted_at: None,
            ChatLog.deleted_by: None,
            ChatLog.deletion_batch_id: None,
        },
        synchronize_session=False,
    )
    restored_sessions = db.query(ChatSession).filter(
        ChatSession.deletion_batch_id == batch_id,
        ChatSession.is_deleted.is_(True),
    ).update(
        {
            ChatSession.is_deleted: False,
            ChatSession.deleted_at: None,
            ChatSession.deleted_by: None,
            ChatSession.deletion_batch_id: None,
        },
        synchronize_session=False,
    )
    if session_ids:
        restored_sessions += db.query(ChatSession).filter(
            ChatSession.id.in_(session_ids),
            ChatSession.is_deleted.is_(True),
        ).update(
            {
                ChatSession.is_deleted: False,
                ChatSession.deleted_at: None,
                ChatSession.deleted_by: None,
                ChatSession.deletion_batch_id: None,
            },
            synchronize_session=False,
        )
    if not restored_logs and not restored_sessions:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục trò chuyện trong thùng rác")
    db.commit()
    log_user_activity(
        db,
        current_user.id,
        "admin_restore_chat_trash",
        {
            "deletion_batch_id": str(batch_id),
            "restored_logs": restored_logs,
            "restored_sessions": restored_sessions,
        },
    )
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"restored_logs": restored_logs, "restored_sessions": restored_sessions}


@router.delete("/trash/chats/{batch_id}")
async def permanently_delete_chat_batch(
    batch_id: UUID,
    confirmation: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    if confirmation != PERMANENT_DELETE_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Cụm từ xác nhận không chính xác")
    deleted_logs, deleted_sessions = _hard_delete_chat_batch(db, batch_id)
    if not deleted_logs and not deleted_sessions:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục trò chuyện trong thùng rác")
    db.commit()
    log_user_activity(
        db,
        current_user.id,
        "admin_permanent_delete_chat_trash",
        {
            "deletion_batch_id": str(batch_id),
            "deleted_logs": deleted_logs,
            "deleted_sessions": deleted_sessions,
        },
    )
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"deleted_logs": deleted_logs, "deleted_sessions": deleted_sessions}


@router.delete("/trash/users/{user_id}")
async def permanently_delete_user(
    user_id: UUID,
    confirmation: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    if confirmation != PERMANENT_DELETE_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Cụm từ xác nhận không chính xác")
    user = _get_manageable_user(db, user_id)
    if not user.is_deleted:
        raise HTTPException(status_code=400, detail="Tài khoản chưa nằm trong thùng rác")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Bạn không thể xóa vĩnh viễn chính mình")
    _anonymize_user(user, datetime.now(timezone.utc))
    db.commit()
    log_user_activity(
        db,
        current_user.id,
        "admin_permanent_delete_user",
        {"target_user_id": str(user_id)},
    )
    await manager.broadcast({"type": "STATS_UPDATED"})
    return {"message": "Đã xóa vĩnh viễn thông tin cá nhân của tài khoản"}


@router.delete("/trash")
async def empty_trash(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_admin(current_user)
    scope = payload.get("scope", "all")
    if scope not in {"chats", "users", "all"}:
        raise HTTPException(status_code=400, detail="Phạm vi dọn thùng rác không hợp lệ")
    if payload.get("confirmation") != PERMANENT_DELETE_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Cụm từ xác nhận không chính xác")

    deleted_logs = deleted_sessions = purged_users = 0
    if scope in {"chats", "all"}:
        for batch_id in _chat_trash_batch_ids(db):
            batch_logs, batch_sessions = _hard_delete_chat_batch(db, batch_id)
            deleted_logs += batch_logs
            deleted_sessions += batch_sessions
    if scope in {"users", "all"}:
        users = db.query(User).filter(
            User.is_deleted.is_(True),
            User.purged_at.is_(None),
            User.id != current_user.id,
        ).all()
        now_utc = datetime.now(timezone.utc)
        for user in users:
            _anonymize_user(user, now_utc)
        purged_users = len(users)

    db.commit()
    result = {
        "deleted_logs": deleted_logs,
        "deleted_sessions": deleted_sessions,
        "purged_users": purged_users,
    }
    log_user_activity(db, current_user.id, "admin_empty_trash", {"scope": scope, **result})
    await manager.broadcast({"type": "STATS_UPDATED"})
    return result


def purge_expired_chat_trash(db: Session, retention_days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    batch_ids = {
        row[0]
        for row in db.query(ChatLog.deletion_batch_id).filter(
            ChatLog.is_deleted.is_(True),
            ChatLog.deleted_at <= cutoff,
            ChatLog.deletion_batch_id.is_not(None),
        ).distinct().all()
    }
    batch_ids.update(
        row[0]
        for row in db.query(ChatSession.deletion_batch_id).filter(
            ChatSession.is_deleted.is_(True),
            ChatSession.deleted_at <= cutoff,
            ChatSession.deletion_batch_id.is_not(None),
        ).distinct().all()
    )
    deleted_logs = deleted_sessions = 0
    for batch_id in batch_ids:
        batch_logs, batch_sessions = _hard_delete_chat_batch(db, batch_id)
        deleted_logs += batch_logs
        deleted_sessions += batch_sessions
    db.commit()
    return {"deleted_logs": deleted_logs, "deleted_sessions": deleted_sessions}
