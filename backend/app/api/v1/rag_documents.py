import hashlib
import logging
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR
from app.db.deps import get_db
from app.db.session import engine
from app.core.websocket import manager
from app.models.rag_document import RagDocument
from app.models.user import User
from app.rag.build_index import INDEX_FILES, build_index
from app.rag.rag_service import activate_resources, load_resources
from app.services.rag_index_transaction import (
    RagRollbackError,
    RagIndexSnapshot,
    rollback_file_changes,
    restore_active_index,
    run_rollback_steps,
    snapshot_active_index,
)
from app.services.rag_document_validation import (
    UnindexableDocumentError,
    find_case_variant_collisions,
    find_unindexed_sources,
)
from app.services.rag_document_sync import (
    sync_rag_documents,
    sync_rag_documents_from_index,
)
from app.services.auth_service import get_current_user_from_token, require_manager_or_admin


router = APIRouter(prefix="/admin/documents", tags=["Admin RAG Documents"])
logger = logging.getLogger(__name__)
_index_lock = threading.Lock()
_progress_lock = threading.Lock()
_RAG_ADVISORY_LOCK_ID = 726_243_001
MAX_PDF_SIZE = 25 * 1024 * 1024
MAX_BATCH_FILES = 20
MAX_BATCH_DELETE_FILES = 100
MAX_BATCH_TOTAL_SIZE = 90 * 1024 * 1024
_index_progress = {
    "active": False,
    "progress": 0,
    "stage": "idle",
    "operation": None,
    "file_name": None,
    "error": None,
}


class BatchDeleteRequest(BaseModel):
    file_names: list[str]


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


def _rebuild_and_reload(
    db: Session,
    *,
    required_sources: tuple[str, ...] = (),
) -> int:
    chunk_count, vector_store, bm25_retriever = build_index(
        return_resources=True,
        progress_callback=lambda progress, stage: _set_index_progress(
            progress=progress,
            stage=stage,
        ),
    )
    unindexed_sources = find_unindexed_sources(
        required_sources,
        vector_store.metadata,
    )
    if unindexed_sources:
        raise UnindexableDocumentError(unindexed_sources)
    sync_rag_documents(db, vector_store.metadata)
    # Do not expose the new resources to requests until their metadata has
    # committed. The caller keeps an on-disk snapshot until this returns.
    activate_resources(vector_store, bm25_retriever)
    return chunk_count


def _snapshot_active_rag_index(temp_dir: str) -> RagIndexSnapshot:
    """Keep a rollback copy until PDF changes and DB metadata both succeed."""
    return snapshot_active_index(
        VECTOR_STORE_DIR,
        os.path.join(temp_dir, "index-backup"),
        INDEX_FILES,
    )


def _restore_active_rag_index(snapshot: RagIndexSnapshot) -> None:
    restore_active_index(snapshot, load_resources)


def _rollback_document_update(
    *,
    restore_files,
    restore_database,
    index_snapshot: RagIndexSnapshot,
) -> None:
    try:
        run_rollback_steps(
            [
                ("document files", restore_files),
                ("database metadata", restore_database),
                ("RAG index", lambda: _restore_active_rag_index(index_snapshot)),
            ]
        )
    except RagRollbackError:
        logger.exception("Document update rollback was incomplete")
        raise


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
        try:
            if acquired:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": _RAG_ADVISORY_LOCK_ID},
                )
        except Exception:
            # Closing the connection also releases a PostgreSQL advisory lock.
            logger.exception("Failed to explicitly release the RAG advisory lock")
        finally:
            try:
                if connection is not None:
                    connection.close()
            except Exception:
                logger.exception("Failed to close the RAG advisory-lock connection")
            finally:
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


_DOCUMENT_STATE_FIELDS = (
    "storage_path",
    "file_size",
    "checksum_sha256",
    "status",
    "chunk_count",
    "uploaded_by",
    "error_message",
    "indexed_at",
    "deleted_at",
    "updated_at",
)


def _document_snapshot(document: RagDocument) -> dict:
    return {
        "id": document.id,
        "values": {
            field: getattr(document, field)
            for field in _DOCUMENT_STATE_FIELDS
        },
    }


def _restore_document_rows(
    db: Session,
    snapshots: dict[str, dict],
    created_names: set[str],
) -> None:
    db.rollback()
    if created_names:
        db.query(RagDocument).filter(
            RagDocument.file_name.in_(created_names)
        ).delete(synchronize_session=False)

    for snapshot in snapshots.values():
        document = db.get(RagDocument, snapshot["id"])
        if document is None:
            continue
        for field, value in snapshot["values"].items():
            setattr(document, field, value)
    db.commit()


def _validate_batch_names(file_names: list[str], *, maximum: int) -> list[str]:
    if not file_names:
        raise HTTPException(status_code=400, detail="Select at least one PDF")
    if len(file_names) > maximum:
        raise HTTPException(
            status_code=400,
            detail=f"A batch must not contain more than {maximum} documents",
        )

    safe_names = [_safe_pdf_name(file_name) for file_name in file_names]
    folded_names = [file_name.casefold() for file_name in safe_names]
    if len(set(folded_names)) != len(folded_names):
        raise HTTPException(
            status_code=400,
            detail="A batch must not contain duplicate file names",
        )
    return safe_names


def _reject_case_variant_collisions(db: Session, requested_names: list[str]) -> None:
    existing_names = {
        row[0]
        for row in db.query(RagDocument.file_name).all()
    }
    if os.path.isdir(RAG_DATA_DIR):
        existing_names.update(
            entry.name
            for entry in os.scandir(RAG_DATA_DIR)
            if entry.is_file() and entry.name.lower().endswith(".pdf")
        )

    collisions = find_case_variant_collisions(requested_names, existing_names)
    if collisions:
        requested, existing = collisions[0]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f'PDF "{requested}" conflicts with existing "{existing}". '
                "Use the exact existing letter case when replacing a document."
            ),
        )


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
        _reject_case_variant_collisions(db, [file_name])
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
            snapshots = (
                {file_name: _document_snapshot(document)}
                if document is not None
                else {}
            )
            created_names = {file_name} if document is None else set()
            index_snapshot = _snapshot_active_rag_index(temp_dir)
            file_change = {
                "target_path": target_path,
                "backup_path": backup_path,
                "had_previous": had_previous,
                "previous_moved": False,
                "new_installed": False,
            }
            try:
                if had_previous:
                    os.replace(target_path, backup_path)
                    file_change["previous_moved"] = True
                os.replace(upload_path, target_path)
                file_change["new_installed"] = True

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

                total_chunks = _rebuild_and_reload(
                    db,
                    required_sources=(file_name,),
                )
            except Exception as exc:
                try:
                    _rollback_document_update(
                        restore_files=lambda: rollback_file_changes([file_change]),
                        restore_database=lambda: _restore_document_rows(
                            db,
                            snapshots,
                            created_names,
                        ),
                        index_snapshot=index_snapshot,
                    )
                except RagRollbackError as rollback_exc:
                    _set_index_progress(
                        active=False,
                        stage="failed",
                        error="RAG index rollback failed",
                    )
                    raise HTTPException(status_code=500, detail=str(rollback_exc)) from rollback_exc
                _set_index_progress(
                    active=False,
                    stage="failed",
                    error="Failed to rebuild RAG index",
                )
                if isinstance(exc, UnindexableDocumentError):
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
                raise HTTPException(status_code=500, detail="Failed to rebuild RAG index") from exc

    _set_index_progress(active=False, progress=100, stage="completed")
    background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
    return {
        "message": "Document uploaded and RAG index rebuilt",
        "document": _serialize_document(document, current_user.username),
        "total_chunks": total_chunks,
    }


@router.post("/batch-upload", status_code=status.HTTP_201_CREATED)
def upload_documents_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Upload up to 20 PDFs and rebuild the RAG index exactly once."""
    _require_document_access(current_user)
    safe_names = _validate_batch_names(
        [file.filename for file in files],
        maximum=MAX_BATCH_FILES,
    )
    os.makedirs(RAG_DATA_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="rag-batch-upload-", dir=RAG_DATA_DIR) as temp_dir:
        staged_dir = os.path.join(temp_dir, "staged")
        backup_dir = os.path.join(temp_dir, "backups")
        os.makedirs(staged_dir)
        os.makedirs(backup_dir)

        staged_documents = []
        total_size = 0
        for index, (upload, file_name) in enumerate(zip(files, safe_names, strict=True)):
            upload_path = os.path.join(staged_dir, f"{index}.pdf")
            checksum = hashlib.sha256()
            size = 0
            with open(upload_path, "wb") as output:
                while chunk := upload.file.read(1024 * 1024):
                    size += len(chunk)
                    total_size += len(chunk)
                    if size > MAX_PDF_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail=f'PDF "{file_name}" must not exceed 25 MB',
                        )
                    if total_size > MAX_BATCH_TOTAL_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="The selected PDFs must not exceed 90 MB in total",
                        )
                    checksum.update(chunk)
                    output.write(chunk)

            with open(upload_path, "rb") as uploaded:
                if uploaded.read(5) != b"%PDF-":
                    raise HTTPException(
                        status_code=400,
                        detail=f'"{file_name}" is not a valid PDF',
                    )
            staged_documents.append(
                {
                    "file_name": file_name,
                    "upload_path": upload_path,
                    "size": size,
                    "checksum": checksum.hexdigest(),
                    "backup_path": os.path.join(backup_dir, f"{index}.pdf"),
                }
            )

        with _document_update_lock():
            _reject_case_variant_collisions(db, safe_names)
            _set_index_progress(
                active=True,
                progress=10,
                stage="preparing_document",
                operation="upload",
                file_name=f"{len(files)} documents",
                error=None,
            )
            existing_documents = {
                document.file_name: document
                for document in db.query(RagDocument).filter(
                    RagDocument.file_name.in_(safe_names)
                ).all()
            }
            snapshots = {
                name: _document_snapshot(document)
                for name, document in existing_documents.items()
            }
            created_names = set(safe_names) - set(existing_documents)
            file_changes: list[dict] = []
            index_snapshot = _snapshot_active_rag_index(temp_dir)

            try:
                for staged in staged_documents:
                    file_name = staged["file_name"]
                    target_path = os.path.join(RAG_DATA_DIR, file_name)
                    had_previous = os.path.isfile(target_path)
                    file_changes.append(
                        {
                            "target_path": target_path,
                            "backup_path": staged["backup_path"],
                            "had_previous": had_previous,
                            "previous_moved": False,
                            "new_installed": False,
                        }
                    )
                    change = file_changes[-1]
                    if had_previous:
                        os.replace(target_path, staged["backup_path"])
                        change["previous_moved"] = True
                    os.replace(staged["upload_path"], target_path)
                    change["new_installed"] = True

                    document = existing_documents.get(file_name)
                    if document is None:
                        document = RagDocument(file_name=file_name, storage_path=target_path)
                        db.add(document)
                    document.storage_path = target_path
                    document.file_size = staged["size"]
                    document.checksum_sha256 = staged["checksum"]
                    document.status = "indexing"
                    document.uploaded_by = current_user.id
                    document.error_message = None
                    document.deleted_at = None

                db.commit()
                total_chunks = _rebuild_and_reload(
                    db,
                    required_sources=tuple(safe_names),
                )
            except Exception as exc:
                try:
                    _rollback_document_update(
                        restore_files=lambda: rollback_file_changes(file_changes),
                        restore_database=lambda: _restore_document_rows(
                            db,
                            snapshots,
                            created_names,
                        ),
                        index_snapshot=index_snapshot,
                    )
                except RagRollbackError as rollback_exc:
                    _set_index_progress(
                        active=False,
                        stage="failed",
                        error="RAG index rollback failed",
                    )
                    raise HTTPException(status_code=500, detail=str(rollback_exc)) from rollback_exc
                _set_index_progress(
                    active=False,
                    stage="failed",
                    error="Failed to rebuild RAG index",
                )
                raise HTTPException(
                    status_code=(422 if isinstance(exc, UnindexableDocumentError) else 500),
                    detail=(
                        str(exc)
                        if isinstance(exc, UnindexableDocumentError)
                        else "Failed to rebuild RAG index; all document changes were rolled back"
                    ),
                ) from exc

    updated_documents = {
        document.file_name: document
        for document in db.query(RagDocument).filter(
            RagDocument.file_name.in_(safe_names)
        ).all()
    }
    _set_index_progress(active=False, progress=100, stage="completed")
    background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
    return {
        "message": "Documents uploaded and RAG index rebuilt once",
        "documents": [
            _serialize_document(updated_documents[name], current_user.username)
            for name in safe_names
        ],
        "uploaded_count": len(safe_names),
        "replaced_count": len(snapshots),
        "total_chunks": total_chunks,
    }


@router.post("/batch-delete")
def delete_documents_batch(
    payload: BatchDeleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Delete up to 100 selected PDFs atomically and rebuild the index once."""
    _require_document_access(current_user)
    safe_names = _validate_batch_names(
        payload.file_names,
        maximum=MAX_BATCH_DELETE_FILES,
    )
    os.makedirs(RAG_DATA_DIR, exist_ok=True)

    with _document_update_lock():
        documents = {
            document.file_name: document
            for document in db.query(RagDocument).filter(
                RagDocument.file_name.in_(safe_names)
            ).all()
        }
        missing_names = [
            name
            for name in safe_names
            if name not in documents and not os.path.isfile(os.path.join(RAG_DATA_DIR, name))
        ]
        if missing_names:
            raise HTTPException(
                status_code=404,
                detail=f"Documents not found: {', '.join(missing_names)}",
            )

        _set_index_progress(
            active=True,
            progress=10,
            stage="preparing_document",
            operation="delete",
            file_name=f"{len(safe_names)} documents",
            error=None,
        )
        snapshots = {
            name: _document_snapshot(document)
            for name, document in documents.items()
        }
        created_names = set(safe_names) - set(documents)

        with tempfile.TemporaryDirectory(prefix="rag-batch-delete-", dir=RAG_DATA_DIR) as temp_dir:
            file_changes: list[dict] = []
            index_snapshot = _snapshot_active_rag_index(temp_dir)
            try:
                for index, file_name in enumerate(safe_names):
                    target_path = os.path.join(RAG_DATA_DIR, file_name)
                    backup_path = os.path.join(temp_dir, f"{index}.pdf")
                    had_previous = os.path.isfile(target_path)
                    if had_previous:
                        file_changes.append(
                            {
                                "target_path": target_path,
                                "backup_path": backup_path,
                                "had_previous": True,
                                "previous_moved": False,
                                "new_installed": False,
                            }
                        )
                        shutil.move(target_path, backup_path)
                        file_changes[-1]["previous_moved"] = True

                    document = documents.get(file_name)
                    if document is None:
                        document = RagDocument(file_name=file_name, storage_path=target_path)
                        db.add(document)
                        documents[file_name] = document
                    document.status = "indexing"
                    document.error_message = None

                db.commit()
                total_chunks = _rebuild_and_reload(db) if file_changes else None
                deleted_at = datetime.now(timezone.utc)
                for document in documents.values():
                    document.status = "deleted"
                    document.deleted_at = deleted_at
                    document.chunk_count = 0
                    document.error_message = None
                db.commit()
            except Exception as exc:
                try:
                    _rollback_document_update(
                        restore_files=lambda: rollback_file_changes(file_changes),
                        restore_database=lambda: _restore_document_rows(
                            db,
                            snapshots,
                            created_names,
                        ),
                        index_snapshot=index_snapshot,
                    )
                except RagRollbackError as rollback_exc:
                    _set_index_progress(
                        active=False,
                        stage="failed",
                        error="RAG index rollback failed",
                    )
                    raise HTTPException(status_code=500, detail=str(rollback_exc)) from rollback_exc
                _set_index_progress(
                    active=False,
                    stage="failed",
                    error="Failed to rebuild RAG index",
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to rebuild RAG index; all document changes were rolled back",
                ) from exc

    _set_index_progress(active=False, progress=100, stage="completed")
    background_tasks.add_task(manager.broadcast, {"type": "STATS_UPDATED"})
    return {
        "message": "Documents deleted and RAG index rebuilt once",
        "deleted": safe_names,
        "deleted_count": len(safe_names),
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
        snapshots = (
            {safe_name: _document_snapshot(document)}
            if document is not None
            else {}
        )
        created_names = {safe_name} if document is None else set()
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
            index_snapshot = _snapshot_active_rag_index(temp_dir)
            file_change = {
                "target_path": target_path,
                "backup_path": backup_path,
                "had_previous": True,
                "previous_moved": False,
                "new_installed": False,
            }
            try:
                shutil.move(target_path, backup_path)
                file_change["previous_moved"] = True
                document.status = "indexing"
                document.error_message = None
                db.commit()
                total_chunks = _rebuild_and_reload(db)
                document.status = "deleted"
                document.deleted_at = datetime.now(timezone.utc)
                document.chunk_count = 0
                db.commit()
            except Exception as exc:
                try:
                    _rollback_document_update(
                        restore_files=lambda: rollback_file_changes([file_change]),
                        restore_database=lambda: _restore_document_rows(
                            db,
                            snapshots,
                            created_names,
                        ),
                        index_snapshot=index_snapshot,
                    )
                except RagRollbackError as rollback_exc:
                    _set_index_progress(
                        active=False,
                        stage="failed",
                        error="RAG index rollback failed",
                    )
                    raise HTTPException(status_code=500, detail=str(rollback_exc)) from rollback_exc
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
