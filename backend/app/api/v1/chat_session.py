from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from uuid import uuid4
from app.db.deps import get_db
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.chat_log import ChatLog
from app.services.auth_service import get_current_user_from_token
from app.schemas.chat_session import ChatSessionResponse, ChatSessionUpdate, ChatHistoryMessage

router = APIRouter(prefix="/chat", tags=["Chat Sessions"])

@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        )
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return sessions

@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def rename_chat_session(
    session_id: str,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    session.title = payload.title
    db.commit()
    db.refresh(session)
    return session

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Soft delete the session and its logs as one restorable trash batch.
    deletion_batch_id = uuid4()
    deleted_at = datetime.now(timezone.utc)
    session.is_deleted = True
    session.deleted_at = deleted_at
    session.deleted_by = current_user.id
    session.deletion_batch_id = deletion_batch_id
    db.query(ChatLog).filter(
        ChatLog.session_id == session.id,
        ChatLog.is_deleted.is_(False),
    ).update(
        {
            ChatLog.is_deleted: True,
            ChatLog.deleted_at: deleted_at,
            ChatLog.deleted_by: current_user.id,
            ChatLog.deletion_batch_id: deletion_batch_id,
        },
        synchronize_session=False,
    )
    db.commit()

    return {"message": "Session soft deleted successfully"}

@router.get("/sessions/{session_id}/history", response_model=List[ChatHistoryMessage])
def get_chat_session_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch logs sorted chronologically (created_at asc)
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id == session.id, ChatLog.is_deleted.is_(False))
        .order_by(ChatLog.created_at.asc())
        .all()
    )

    messages = []
    for log in logs:
        # Convert single log row into User Question message
        messages.append({
            "id": f"{log.id}_q",
            "role": "user",
            "content": log.question,
            "timestamp": log.created_at
        })
        
        # Convert single log row into Assistant Answer message
        if log.answer:
            messages.append({
                "id": f"{log.id}_a",
                "role": "assistant",
                "content": log.answer,
                "timestamp": log.created_at
            })

    return messages
