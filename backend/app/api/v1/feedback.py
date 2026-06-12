from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.db.deps import get_db
from app.models.user import User
from app.models.chat_log import ChatLog
from app.models.feedback_log import FeedbackLog
from app.services.auth_service import get_current_user_from_token, require_manager_or_admin
from app.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackResolve
from app.core.websocket import manager

router = APIRouter(tags=["Feedbacks"])


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    # Verify the chat log exists and belongs to the user (optional check, but good for security)
    chat_log = db.query(ChatLog).filter(ChatLog.id == payload.chat_id).first()
    if not chat_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat log not found"
        )

    # Check if feedback already exists for this chat_log to update or create
    existing_feedback = db.query(FeedbackLog).filter(
        FeedbackLog.chat_id == payload.chat_id,
        FeedbackLog.is_deleted == False
    ).first()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.rating = payload.rating
        existing_feedback.comment = payload.comment
        existing_feedback.user_id = current_user.id
        existing_feedback.created_at = datetime.now(timezone.utc)  # update timestamp
        db.commit()
        db.refresh(existing_feedback)
        feedback = existing_feedback
    else:
        # Create new feedback
        feedback = FeedbackLog(
            user_id=current_user.id,
            chat_id=payload.chat_id,
            rating=payload.rating,
            comment=payload.comment
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

    # Broadcast stats update to admin dashboard
    try:
        await manager.broadcast({"type": "STATS_UPDATED"})
    except Exception:
        pass

    return feedback


@router.get("/admin/feedbacks", response_model=List[FeedbackResponse])
def get_admin_feedbacks(
    is_resolved: Optional[bool] = None,
    rating: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_manager_or_admin(current_user)

    # Query with outerjoin to avoid losing feedbacks when related rows are set to NULL
    query = db.query(FeedbackLog).filter(FeedbackLog.is_deleted == False)

    if is_resolved is not None:
        query = query.filter(FeedbackLog.is_resolved == is_resolved)

    if rating is not None and rating != "all":
        query = query.filter(FeedbackLog.rating == rating)

    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(ChatLog, FeedbackLog.chat_id == ChatLog.id).outerjoin(User, FeedbackLog.user_id == User.id)
        query = query.filter(
            (FeedbackLog.comment.ilike(search_pattern)) |
            (ChatLog.question.ilike(search_pattern)) |
            (ChatLog.answer.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (User.username.ilike(search_pattern))
        )

    feedbacks = query.order_by(FeedbackLog.created_at.desc()).all()
    return feedbacks


@router.put("/admin/feedbacks/{feedback_id}/resolve", response_model=FeedbackResponse)
async def resolve_feedback(
    feedback_id: UUID,
    payload: FeedbackResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_manager_or_admin(current_user)

    feedback = db.query(FeedbackLog).filter(
        FeedbackLog.id == feedback_id,
        FeedbackLog.is_deleted == False
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    feedback.is_resolved = payload.is_resolved
    if payload.is_resolved:
        feedback.resolved_at = datetime.now(timezone.utc)
        feedback.resolved_by = current_user.id
    else:
        feedback.resolved_at = None
        feedback.resolved_by = None

    db.commit()
    db.refresh(feedback)

    # Broadcast update
    try:
        await manager.broadcast({"type": "STATS_UPDATED"})
    except Exception:
        pass

    return feedback


@router.delete("/admin/feedbacks/{feedback_id}")
async def delete_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_manager_or_admin(current_user)

    feedback = db.query(FeedbackLog).filter(
        FeedbackLog.id == feedback_id,
        FeedbackLog.is_deleted == False
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Soft delete
    feedback.is_deleted = True
    db.commit()

    # Broadcast update
    try:
        await manager.broadcast({"type": "STATS_UPDATED"})
    except Exception:
        pass

    return {"message": "Feedback soft deleted successfully"}
