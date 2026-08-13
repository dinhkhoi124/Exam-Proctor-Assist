import hashlib
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR
from app.db.deps import get_db
from app.db.session import engine
from app.core.websocket import manager
from app.models.rag_document import RagDocument
from app.models.user import User
from app.rag.build_index import build_index
from app.rag.rag_service import activate_resources
from app.services.rag_document_sync import (
    sync_rag_documents,
    sync_rag_documents_from_index,
)
from app.services.auth_service import get_current_user_from_token, require_manager_or_admin


router = APIRouter(prefix="/admin/documents", tags=["Admin RAG Documents"])
_index_lock = threading.Lock()
_progress_lock = threading.Lock()
_RAG_ADVISORY_LOCK_ID = 726_243_001
MAX_PDF_SIZE = 25 * 1024 * 1024
_index_progress = {
    "active": False,
    "progress": 0,
    "stage": "idle",
    "operation": None,
    "file_name": None,
    "error": None,
}


def _require_document_access(user: User) -> None:
    require_manager_or_admin(user)


def _safe_pdf_name(raw_name: str | None) -> str:
    if not raw_name:
        raise HTTPException(status_code=400, detail="File name is required")

    normalized = raw_name.replace("\\", "/")
    file_name = normalized.rsplit("/", 1)[-1].strip()
    if (
        not file_name
        or file_name in {".", ".."}
        or Path(file_name).suffix.lower() != ".pdf"
        or any(ord(char) < 32 for char in file_name)
    ):
        raise HTTPException(status_code=400, detail="Only valid PDF file names are allowed")
    return file_name


def _set_index_progress(**changes) -> None:
    with _progress_lock:
        _index_progress.update(changes)


def _get_index_progress() -> dict:
    with _progress_lock:
        return dict(_index_progress)


def _rebuild_and_reload(db: Session) -> int:
    chunk_count, vector_store, bm25_retriever = build_index(
        return_resources=True,
        progress_callback=lambda progress, stage: _set_index_progress(
            progress=progress,
            stage=stage,
        ),
    )
    activate_resources(vector_store, bm25_retriever)
    sync_rag_documents(db, vector_store.metadata)
    return chunk_count


@contextmanager
def _document_update_lock():
    if not _index_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another document update is already rebuilding the index",
        )

    connection = None
    acquired = False
    try:
        connection = engine.connect()
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": _RAG_ADVISORY_LOCK_ID},
            ).scalar()
        )
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another server is already rebuilding the RAG index",
            )
        yield
    finally:
        if acquired:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": _RAG_ADVISORY_LOCK_ID},
            )
        if connection is not None:
            connection.close()
        _set_index_progress(active=False)
        _index_lock.release()


def _serialize_document(document: RagDocument, uploader_name: str | None = None) -> dict:
    return {
        "id": str(document.id),
        "name": document.file_name,
        "size": document.file_size,
        "updated_at": document.updated_at.timestamp(),
        "chunk_count": document.chunk_count,
        "indexed": document.status == "ready",
        "status": document.status,
        "uploaded_by": str(document.uploaded_by) if document.uploaded_by else None,
        "uploader_name": uploader_name,
        "error_message": document.error_message,
    }


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    _require_document_access(current_user)
    sync_rag_documents_from_index(db, refresh_existing=False)
    documents = (
        db.query(RagDocument, User.username)
        .outerjoin(User, RagDocument.uploaded_by == User.id)
        .filter(RagDocument.status != "deleted")
        .order_by(RagDocument.updated_at.desc())
        .all()
    )
    return [_serialize_document(document, username) for document, username in documents]


@router.get("/index-status")
def get_index_status(current_user: User = Depends(get_current_user_from_token)):
    _require_document_access(current_user)
    return _get_index_progress()


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    _require_document_access(current_user)
    file_name = _safe_pdf_name(file.filename)
    os.makedirs(RAG_DATA_DIR, exist_ok=True)
    target_path = os.path.join(RAG_DATA_DIR, file_name)

    with _document_update_lock():
        _set_index_progress(
            active=True,
            progress=10,
            stage="preparing_document",
            operation="upload",
            file_name=file_name,
            error=None,
        )
        document = db.query(RagDocument).filter(RagDocument.file_name == file_name).first()
        with tempfile.TemporaryDirectory(prefix="rag-upload-", dir=RAG_DATA_DIR) as temp_dir:
            upload_path = os.path.join(temp_dir, file_name)
            checksum = hashlib.sha256()
            size = 0
            with open(upload_path, "wb") as output:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_PDF_SIZE:
                        raise HTTPException(status_code=413, detail="PDF must not exceed 25 MB")
                    checksum.update(chunk)
                    output.write(chunk)

            with open(upload_path, "rb") as uploaded:
                if uploaded.read(5) != b"%PDF-":
                    raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

            backup_path = os.path.join(temp_dir, "previous.pdf")
            had_previous = os.path.exists(target_path)
            if had_previous:
                os.replace(target_path, backup_path)
            os.replace(upload_path, target_path)

            if document is None:
                document = RagDocument(file_name=file_name, storage_path=target_path)
                db.add(document)
            document.storage_path = target_path
            document.file_size = size
            document.checksum_sha256 = checksum.hexdigest()
            document.status = "indexing"
            document.uploaded_by = current_user.id
            document.error_message = None
            document.deleted_at = None
            db.commit()

            try:
                total_chunks = _rebuild_and_reload(db)
            except Exception as exc:
                if os.path.exists(target_path):
                    os.remove(target_path)
                if had_previous:
                    os.replace(backup_path, target_path)
                document.status = "ready" if had_previous else "failed"
                document.error_message = f"Indexing failed: {str(exc)[:1000]}"
                db.commit()
                _set_index_progress(
                    active=False,
                    stage="failed",
                    error="Failed to rebuild RAG index",
                )
                raise HTTPException(status_code=500, detail="Failed to rebuild RAG index") from exc

    _set_index_progress(active=False, progress=100, stage="completed")
    background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
    return {
        "message": "Document uploaded and RAG index rebuilt",
        "document": _serialize_document(document, current_user.username),
        "total_chunks": total_chunks,
    }


@router.delete("/{file_name}")
def delete_document(
    file_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    _require_document_access(current_user)
    safe_name = _safe_pdf_name(file_name)
    document = db.query(RagDocument).filter(RagDocument.file_name == safe_name).first()
    target_path = os.path.join(RAG_DATA_DIR, safe_name)
    if document is None and not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="Document not found")

    with _document_update_lock():
        _set_index_progress(
            active=True,
            progress=10,
            stage="preparing_document",
            operation="delete",
            file_name=safe_name,
            error=None,
        )
        if document is None:
            document = RagDocument(file_name=safe_name, storage_path=target_path)
            db.add(document)

        if not os.path.isfile(target_path):
            document.status = "deleted"
            document.deleted_at = datetime.now(timezone.utc)
            db.commit()
            _set_index_progress(active=False, progress=100, stage="completed")
            background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
            return {"message": "Document metadata deleted", "name": safe_name}

        with tempfile.TemporaryDirectory(prefix="rag-delete-", dir=RAG_DATA_DIR) as temp_dir:
            backup_path = os.path.join(temp_dir, safe_name)
            shutil.move(target_path, backup_path)
            document.status = "indexing"
            document.error_message = None
            db.commit()
            try:
                total_chunks = _rebuild_and_reload(db)
                document.status = "deleted"
                document.deleted_at = datetime.now(timezone.utc)
                document.chunk_count = 0
                db.commit()
            except Exception as exc:
                shutil.move(backup_path, target_path)
                document.status = "ready"
                document.error_message = f"Delete indexing failed: {str(exc)[:1000]}"
                db.commit()
                _set_index_progress(
                    active=False,
                    stage="failed",
                    error="Failed to rebuild RAG index",
                )
                raise HTTPException(status_code=500, detail="Failed to rebuild RAG index") from exc

    _set_index_progress(active=False, progress=100, stage="completed")
    background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
    return {
        "message": "Document deleted and RAG index rebuilt",
        "name": safe_name,
        "total_chunks": total_chunks,
    }
